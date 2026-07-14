"""Database engine, session factory, and the FastAPI session dependency.

SQLAlchemy 2.0 style. One engine per process; one session per request.

Why a session-per-request (via `get_db`)? A Session is a unit-of-work holding an
identity map and pending changes. Sharing one across requests would leak state
and break under concurrency. Creating one per request — opened when the request
starts, closed when it ends — keeps each request isolated. FastAPI's dependency
injection makes this a one-liner in route signatures: `db: Session = Depends(get_db)`.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite needs `check_same_thread=False` because FastAPI may touch a session from
# a different thread than the one that created it. This arg is invalid for other
# drivers, so we only pass it for SQLite.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    # Log SQL in development only; noisy in production.
    echo=settings.DEBUG and _is_sqlite,
    # Verify a connection is alive before using it (matters for Postgres later).
    pool_pre_ping=True,
)

# autoflush=False: we control when pending changes hit the DB (explicit commits),
# avoiding surprise flushes mid-request.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base all ORM models inherit from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables for the MVP.

    Importing the models module registers them on `Base.metadata` before we call
    `create_all`. This is fine while the schema is young; production migrations
    (Alembic) are the later upgrade — see ENGINEERING_NOTES.
    """
    # Imported for the side effect of registering models on Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
