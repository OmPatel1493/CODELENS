"""Embedded ChromaDB vector index.

Chroma runs in-process and persists to a local directory (no server, no cost).
Each repository gets its own collection so search is naturally scoped and deleting
a repo is a single `delete_collection`. We pass our own embeddings (from the
embedder service), so Chroma never invokes its default embedding function.

The persisted directory is what gets snapshotted to object storage (S3) for
durability across App Service restarts — see the ADR.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache
def _get_client(path: str):
    import chromadb

    return chromadb.PersistentClient(path=path)


def get_client():
    from app.core.config import settings

    return _get_client(settings.CHROMA_DIR)


# ChromaDB rejects a single add/upsert larger than its internal max batch size
# (~5.4k). We chunk upserts below that so large repos index without error.
_MAX_UPSERT_BATCH = 5000


def _collection_name(repository_id: int) -> str:
    return f"repo_{repository_id}"


def _collection(repository_id: int):
    # cosine space — our embeddings are normalized, so cosine == dot product.
    return get_client().get_or_create_collection(
        name=_collection_name(repository_id),
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    repository_id: int,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    if not ids:
        return
    collection = _collection(repository_id)
    # Chunk the upsert so a large repo can't exceed Chroma's max batch size.
    for start in range(0, len(ids), _MAX_UPSERT_BATCH):
        end = start + _MAX_UPSERT_BATCH
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )


def query(
    repository_id: int, query_embedding: list[float], n_results: int = 5
) -> list[dict[str, Any]]:
    """Return the nearest chunks: [{id, document, metadata, distance}, ...]."""
    result = _collection(repository_id).query(
        query_embeddings=[query_embedding], n_results=n_results
    )
    ids = result["ids"][0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {"id": ids[i], "document": documents[i], "metadata": metadatas[i], "distance": distances[i]}
        for i in range(len(ids))
    ]


def delete_repository_index(repository_id: int) -> None:
    try:
        get_client().delete_collection(name=_collection_name(repository_id))
    except Exception:
        # Collection may never have been created (e.g. ingestion failed early).
        pass


def snapshot_to_storage(storage) -> str | None:
    """Archive the persisted Chroma directory and save it to object storage.

    Realizes the ADR's "exported index → S3": the index becomes durable across
    App Service restarts (local disk there is ephemeral). Returns the storage key.
    """
    import io
    import os
    import tarfile

    from app.core.config import settings

    if not os.path.isdir(settings.CHROMA_DIR):
        return None
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
        tf.add(settings.CHROMA_DIR, arcname="chroma")
    key = "index/chroma-snapshot.tar.gz"
    storage.save_bytes(key, buffer.getvalue())
    return key
