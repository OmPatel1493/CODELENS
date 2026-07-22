"""Logging configuration.

One place to set the log format and level. Called once at startup. In production
(DEBUG off) SQLAlchemy's engine logging is quieted so logs stay readable; request
access logging is handled by a middleware in `main.py`.
"""

import logging

from app.core.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # SQLAlchemy echo is controlled separately (settings.DEBUG); keep its logger
    # from double-emitting at INFO in production.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
