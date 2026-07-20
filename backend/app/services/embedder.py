"""Text embedding via sentence-transformers.

The model (~80 MB) is loaded lazily on first use and cached for the process — we
don't want to pay the load cost at import time (it would slow startup and tests
that never embed). `all-MiniLM-L6-v2` is small, fast on CPU, and 384-dimensional.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache
def _get_model():
    # Imported here so importing this module doesn't drag in torch until needed.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into vectors (normalized for cosine similarity)."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


@lru_cache(maxsize=512)
def embed_query(text: str) -> list[float]:
    """Embed a single search query.

    Cached: identical queries (a repeated search, or a search and a bug-localize
    with the same text) skip the model call entirely. Callers must treat the
    returned list as read-only since it's shared across cache hits.
    """
    return embed_texts([text])[0]
