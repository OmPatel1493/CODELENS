"""RAG answer layer — synthesize a cited answer over retrieved code.

Pipeline: reuse semantic search to retrieve the most relevant chunks, feed them
to an LLM as grounding context, and return a natural-language answer with inline
[n] citations plus the source chunks. The LLM sits behind an ``LLMBackend``
interface (same Strategy pattern as storage/embeddings): the default talks to any
OpenAI-compatible chat-completions endpoint (Groq by default), so the provider is
a config swap, not a code change.

Retrieval stays the source of truth — the model only rephrases what the code says,
and is instructed to refuse when the answer isn't in the provided context. This
keeps the feature grounded (no hallucinated APIs) and interpretable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.repository import Repository
from app.schemas.search import SearchHit
from app.services import search_service

_SYSTEM_PROMPT = (
    "You are CodeLens, a precise coding assistant. Answer the user's question about "
    "THIS codebase using ONLY the numbered code snippets provided as context. Cite the "
    "snippets you rely on with inline markers like [1] or [2] matching their numbers. "
    "If the context does not contain enough to answer, say so plainly instead of "
    "guessing. Be concise and technical, and format with markdown."
)


class LLMBackend(ABC):
    """Turns a system + user prompt into a completion string."""

    @abstractmethod
    def complete(
        self, system: str, user: str, *, json_mode: bool = False, max_tokens: int = 800
    ) -> str: ...


class OpenAICompatibleLLM(LLMBackend):
    """Chat-completions over any OpenAI-compatible endpoint (Groq by default)."""

    def __init__(self, url: str, api_key: str, model: str, timeout: float) -> None:
        self._url = url
        self._model = model
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self, system: str, user: str, *, json_mode: bool = False, max_tokens: int = 800
    ) -> str:
        import httpx

        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,  # low: we want faithful synthesis, not creativity
            "max_tokens": max_tokens,
        }
        if json_mode:  # ask for a strict JSON object (OpenAI/Groq JSON mode)
            body["response_format"] = {"type": "json_object"}
        resp = httpx.post(self._url, headers=self._headers, json=body, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


@lru_cache
def get_llm() -> LLMBackend:
    """Return the configured LLM backend (built once per process)."""
    if not settings.LLM_API_KEY:
        raise RuntimeError(
            "AI features are not configured: set LLM_API_KEY (e.g. a free Groq key) "
            "to enable Ask and Code Review."
        )
    return OpenAICompatibleLLM(
        settings.LLM_API_URL, settings.LLM_API_KEY, settings.LLM_MODEL, settings.LLM_TIMEOUT
    )


def _build_context(hits: list[SearchHit]) -> str:
    """Render retrieved chunks as a numbered context block for the prompt."""
    blocks = []
    for i, h in enumerate(hits, start=1):
        symbol = f" :: {h.symbol_name}" if h.symbol_name else ""
        header = f"[{i}] {h.file_path}{symbol} (lines {h.start_line}-{h.end_line})"
        blocks.append(f"{header}\n```\n{h.snippet}\n```")
    return "\n\n".join(blocks)


def answer_question(
    db: Session, repo: Repository, query: str, limit: int
) -> tuple[str, list[SearchHit]]:
    """Retrieve grounding chunks, then synthesize a cited answer over them."""
    hits = search_service.search_repository(db, repo, query, limit)
    if not hits:
        return (
            "I couldn't find anything relevant in this repository's indexed code to answer that.",
            [],
        )
    user_prompt = f"Question: {query}\n\nContext snippets:\n\n{_build_context(hits)}"
    answer = get_llm().complete(_SYSTEM_PROMPT, user_prompt)
    return answer, hits
