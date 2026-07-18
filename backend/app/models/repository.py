"""Repository model — an indexed codebase belonging to a user."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.code_chunk import CodeChunk
    from app.models.user import User


class RepoSource(enum.StrEnum):
    """Where the repository came from."""

    github = "github"
    upload = "upload"


class RepoStatus(enum.StrEnum):
    """Indexing lifecycle. The frontend progress page reads this field."""

    pending = "pending"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class Repository(Base, TimestampMixin):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[RepoSource] = mapped_column(Enum(RepoSource))
    status: Mapped[RepoStatus] = mapped_column(Enum(RepoStatus), default=RepoStatus.pending)

    # For github repos: the source URL. NULL for uploads.
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Storage key of the archived source (in the configured storage backend).
    archive_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Number of files discovered during ingestion.
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    # Populated with the reason when status == failed.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="repositories")
    chunks: Mapped[list[CodeChunk]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
