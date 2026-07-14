"""Health check endpoints.

`/health` proves the service is up. `/health/db` additionally runs a trivial query
to prove the database is reachable — useful for deploy readiness probes, since an
app can be "up" while its database is unreachable.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])

# Reusable typed dependency — the current FastAPI idiom (avoids a call in defaults).
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/db")
def health_db(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
