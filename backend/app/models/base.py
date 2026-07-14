"""Shared model mixins."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds a DB-populated `created_at` column.

    `server_default=func.now()` lets the database set the timestamp, so it's
    correct even for rows inserted outside the app (migrations, scripts).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
