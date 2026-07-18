"""Parse → embed → store pipeline.

Given an ingested archive, walk its source files, chunk each with tree-sitter,
persist chunk metadata in SQL, embed the chunk texts, and write the vectors to the
per-repository ChromaDB collection. Chunk rows and Chroma documents share the same
id (the SQL primary key), so a vector hit maps straight back to its source.
"""

from __future__ import annotations

import io
import tarfile
import zipfile
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.code_chunk import CodeChunk
from app.models.repository import Repository
from app.services import embedder, vector_store
from app.services.chunker import chunk_file


def _normalize_path(path: str, ext: str) -> str:
    # GitHub tarballs wrap everything in a top-level "<owner>-<repo>-<sha>/" dir;
    # strip it so stored paths are repo-relative.
    if ext != "zip" and "/" in path:
        return path.split("/", 1)[1]
    return path


def _is_code_file(path: str, size: int, allowed_exts: set[str]) -> bool:
    if size == 0 or size > settings.MAX_FILE_BYTES:
        return False
    dot = path.rfind(".")
    return dot != -1 and path[dot:].lower() in allowed_exts


def iter_archive_files(data: bytes, ext: str) -> Iterator[tuple[str, bytes]]:
    """Yield (path, bytes) for each file in a .zip or .tar.gz archive."""
    if ext == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if not info.is_dir():
                    yield info.filename, zf.read(info)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile():
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        yield member.name, extracted.read()


def index_repository(db: Session, repo: Repository, archive_bytes: bytes, ext: str) -> int:
    """Chunk, embed, and store the repo's source. Returns the number of chunks."""
    allowed = {e.lower() for e in settings.CODE_EXTENSIONS}

    rows: list[CodeChunk] = []
    for raw_path, raw in iter_archive_files(archive_bytes, ext):
        path = _normalize_path(raw_path, ext)
        if not _is_code_file(path, len(raw), allowed):
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue  # skip binary / non-UTF8 files
        for pc in chunk_file(path, text):
            rows.append(
                CodeChunk(
                    repository_id=repo.id,
                    file_path=path,
                    symbol_name=pc.symbol_name,
                    kind=pc.kind,
                    start_line=pc.start_line,
                    end_line=pc.end_line,
                    content=pc.content,
                )
            )

    if not rows:
        return 0

    db.add_all(rows)
    db.commit()  # assigns primary keys used as Chroma ids

    embeddings = embedder.embed_texts([row.content for row in rows])
    vector_store.add_chunks(
        repo.id,
        ids=[str(row.id) for row in rows],
        embeddings=embeddings,
        documents=[row.content for row in rows],
        metadatas=[
            {
                "file_path": row.file_path,
                "symbol_name": row.symbol_name or "",
                "kind": str(row.kind),
                "start_line": row.start_line,
                "end_line": row.end_line,
            }
            for row in rows
        ],
    )
    for row in rows:
        row.is_embedded = True
    db.commit()
    return len(rows)
