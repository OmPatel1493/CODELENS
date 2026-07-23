"""Text embedding — pluggable backend (Strategy), mirroring services/storage.py.

Callers use the module-level ``embed_texts`` / ``embed_query`` and never see the
concrete backend. Which backend runs is one env var (``EMBEDDING_BACKEND``):

* ``LocalEmbedder`` — sentence-transformers on-box. Free and offline; the dev
  default. Requires the optional ``local`` extra (``uv sync --extra local``),
  which pulls torch (~2 GB) — deliberately *not* installed in the deploy image.
* ``ApiEmbedder`` — a hosted embedding API over HTTP, so the deployed backend
  carries no torch and fits a small (512 MB) free host. Defaults to the Hugging
  Face Inference API serving the *same* model as local dev, so the vectors are
  identical (384-dim) and an index built locally stays query-compatible.

This is the same dependency-inversion trade as ``STORAGE_BACKEND``: zero-cost,
offline development on the full ML stack; a slim, free-hostable image in prod.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings


def _normalize(vec: list[float]) -> list[float]:
    """Scale to unit length so dot product == cosine similarity (Chroma's space)."""
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class EmbeddingBackend(ABC):
    """Turns a batch of texts into unit-normalized vectors."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder(EmbeddingBackend):
    """On-box sentence-transformers. Loads the model (and torch) lazily, once."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "EMBEDDING_BACKEND=local requires the 'local' extra "
                    "(`uv sync --extra local`, pulls torch). For a slim, "
                    "free-hostable deploy set EMBEDDING_BACKEND=api instead."
                ) from exc
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._get_model().encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


class ApiEmbedder(EmbeddingBackend):
    """Hosted embedding API over HTTP (default: HF Inference API, same model).

    Stateless and torch-free — just an HTTPS call — so the deploy image stays
    small. Results are unit-normalized here to match ``LocalEmbedder`` exactly.
    """

    def __init__(self, url: str, token: str, timeout: float) -> None:
        self._url = url
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        import httpx

        resp = httpx.post(
            self._url,
            headers=self._headers,
            # wait_for_model rides out the API's cold start instead of erroring.
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        vectors = resp.json()
        if not isinstance(vectors, list) or (vectors and not isinstance(vectors[0], list)):
            raise RuntimeError(f"Unexpected embedding API response shape: {type(vectors)}")
        return [_normalize(v) for v in vectors]


@lru_cache
def get_embedder() -> EmbeddingBackend:
    """Return the configured embedding backend (built once per process)."""
    if settings.EMBEDDING_BACKEND == "api":
        url = settings.EMBEDDING_API_URL or (
            f"https://api-inference.huggingface.co/models/{settings.EMBEDDING_MODEL}"
        )
        return ApiEmbedder(url, settings.HF_API_TOKEN, settings.EMBEDDING_API_TIMEOUT)
    return LocalEmbedder()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into vectors (normalized for cosine similarity)."""
    return get_embedder().embed(texts)


@lru_cache(maxsize=512)
def embed_query(text: str) -> list[float]:
    """Embed a single search query.

    Cached: identical queries (a repeated search, or a search and a bug-localize
    with the same text) skip the backend call entirely. Callers must treat the
    returned list as read-only since it's shared across cache hits.
    """
    return embed_texts([text])[0]
