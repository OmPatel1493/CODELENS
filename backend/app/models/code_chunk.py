"""CodeChunk model — one parsed unit (file, class, or function) of a repository.

This is the metadata half of the search index. The embedding itself lives in the
FAISS vector index; `vector_id` is the integer position FAISS assigns, and it's
how we map a vector-search hit back to its source code here. Designing that
bridge column in now avoids a schema migration when the indexing pipeline lands.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
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
    # Position of this chunk's embedding in the FAISS index. NULL until embedded.
    vector_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    repository: Mapped[Repository] = relationship(back_populates="chunks")
