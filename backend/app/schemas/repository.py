"""Repository request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.repository import RepoSource, RepoStatus


class GithubIngestRequest(BaseModel):
    """Ingest a public GitHub repository by URL."""

    url: str = Field(
        min_length=1,
        max_length=1024,
        examples=["https://github.com/pallets/flask"],
    )


class RepoStats(BaseModel):
    """Aggregate counts for the current user's dashboard."""

    repositories: int
    indexed_chunks: int
    searches_run: int


class RecentSearch(BaseModel):
    query: str
    result_count: int
    created_at: datetime


class RepoAnalytics(BaseModel):
    """Per-repository breakdown for the analytics view."""

    kind_breakdown: dict[str, int]
    language_breakdown: dict[str, int]
    recent_searches: list[RecentSearch]


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source: RepoSource
    status: RepoStatus
    source_url: str | None
    file_count: int
    error_message: str | None
    created_at: datetime
