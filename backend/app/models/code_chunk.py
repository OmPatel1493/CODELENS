"""CodeChunk model — one parsed unit (file, class, or function) of a repository.

This is the metadata half of the search index. The embedding vector lives in the
ChromaDB index, stored under this row's own id (as a string). We don't need a
separate position column (as FAISS would require) — Chroma addresses vectors by id.
`is_embedded` marks whether this chunk's vector has been written to Chroma yet.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class ChunkKind(enum.StrEnum):
    file = "file"
    class_ = "class"
    function = "function"


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024))
    # NULL for whole-file chunks that have no symbol name.
    symbol_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[ChunkKind] = mapped_column(Enum(ChunkKind))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    # Whether this chunk's embedding has been written to the Chroma index.
    # The Chroma document id is str(self.id).
    is_embedded: Mapped[bool] = mapped_column(Boolean, default=False)

    repository: Mapped[Repository] = relationship(back_populates="chunks")
