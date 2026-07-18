"""Health check endpoints.

`/health` proves the service is up. `/health/db` additionally runs a trivial query
to prove the database is reachable — useful for deploy readiness probes, since an
app can be "up" while its database is unreachable.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings

router = APIRouter(tags=["health"])


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
