"""Semantic search over a repository's indexed chunks.

Embed the query into the same space as the code chunks, ask ChromaDB for the
nearest vectors, then map those hits back to their `CodeChunk` rows for
authoritative content and metadata. Each search is logged (for the stats/analytics).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.models.repository import Repository
from app.models.search_log import SearchLog
from app.schemas.search import SearchHit
from app.services import embedder, vector_store

_SNIPPET_MAX_LINES = 40
_SNIPPET_MAX_CHARS = 2000


def _snippet(content: str) -> str:
    text = "\n".join(content.splitlines()[:_SNIPPET_MAX_LINES])
    if len(text) > _SNIPPET_MAX_CHARS:
        text = text[:_SNIPPET_MAX_CHARS] + "\n…"
    return text


def search_repository(db: Session, repo: Repository, query: str, limit: int) -> list[SearchHit]:
    query_vector = embedder.embed_query(query)
    raw_hits = vector_store.query(repo.id, query_vector, n_results=limit)

    results: list[SearchHit] = []
    for hit in raw_hits:
        chunk = db.get(CodeChunk, int(hit["id"]))
        if chunk is None:
            continue
        # Chroma cosine distance ≈ 1 - similarity; turn it into a 0..1 confidence.
        distance = hit.get("distance") or 0.0
        score = max(0.0, min(1.0, 1.0 - distance))
        results.append(
            SearchHit(
                chunk_id=chunk.id,
                file_path=chunk.file_path,
                symbol_name=chunk.symbol_name,
                kind=chunk.kind,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                snippet=_snippet(chunk.content),
                score=round(score, 4),
            )
        )

    db.add(SearchLog(repository_id=repo.id, query=query, result_count=len(results)))
    db.commit()
    return results
