"""User model.

The table shape (including `hashed_password`) lands here; the auth flow that
populates it — registration, hashing, login — arrives in the next feature.
We store only a password *hash*, never a plaintext password.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    repositories: Mapped[list[Repository]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
