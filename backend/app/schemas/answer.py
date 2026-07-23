"""RAG answer (Ask) request/response schemas."""

from pydantic import BaseModel, Field

from app.schemas.search import SearchHit


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1024)
    # How many retrieved chunks to ground the answer on (also the sources shown).
    limit: int = Field(default=6, ge=1, le=12)


class AskResponse(BaseModel):
    query: str
    # The synthesized natural-language answer (markdown, with inline [n] citations).
    answer: str
    # The retrieved chunks used as context — [1], [2]… map to these in order.
    sources: list[SearchHit]
