"""SearchLog — one row per semantic search, powering the "searches run" stat
and (in the analytics milestone) query history."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class SearchLog(Base, TimestampMixin):
    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    query: Mapped[str] = mapped_column(String(1024))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
