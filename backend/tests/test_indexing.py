"""Indexing pipeline test — embedder and vector store are mocked so it's fast."""

import io
import zipfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.models.repository import Repository, RepoSource
from app.models.user import User
from app.services import indexing_service


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def test_index_repository_creates_embedded_chunks(db_session: Session, monkeypatch):
    added: dict = {}
    monkeypatch.setattr(
        indexing_service.embedder,
        "embed_texts",
        lambda texts: [[0.0, 0.1, 0.2] for _ in texts],
    )
    monkeypatch.setattr(
        indexing_service.vector_store,
        "add_chunks",
        lambda *args, **kwargs: added.update(count=len(kwargs.get("ids", []))),
    )

    user = User(email="idx@codelens.io", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.upload)
    db_session.add(repo)
    db_session.commit()

    # a.py is code (chunked); the .md file is skipped (not a code extension).
    data = _zip({"a.py": "def f():\n    return 1\n", "README.md": "# docs"})

    n = indexing_service.index_repository(db_session, repo, data, "zip")

    assert n >= 1
    rows = list(db_session.scalars(select(CodeChunk)))
    assert len(rows) == n
    assert all(row.is_embedded for row in rows)
    assert added["count"] == n  # vectors were written to the store


def test_index_repository_with_no_code_files_returns_zero(db_session: Session, monkeypatch):
    monkeypatch.setattr(indexing_service.embedder, "embed_texts", lambda texts: [])
    monkeypatch.setattr(indexing_service.vector_store, "add_chunks", lambda *a, **k: None)

    user = User(email="empty@codelens.io", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    repo = Repository(owner_id=user.id, name="demo", source=RepoSource.upload)
    db_session.add(repo)
    db_session.commit()

    data = _zip({"README.md": "# docs", "image.png": "not code"})
    assert indexing_service.index_repository(db_session, repo, data, "zip") == 0
