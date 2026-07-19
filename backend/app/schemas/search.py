"""Semantic search request/response schemas."""

from pydantic import BaseModel, Field

from app.models.code_chunk import ChunkKind


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1024)
    limit: int = Field(default=5, ge=1, le=25)


class SearchHit(BaseModel):
    chunk_id: int
    file_path: str
    symbol_name: str | None
    kind: ChunkKind
    start_line: int
    end_line: int
    snippet: str
    # 0..1 semantic-similarity confidence (1 = closest match).
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]
