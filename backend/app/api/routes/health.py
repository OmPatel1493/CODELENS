"""Health check endpoint.

A trivial route that proves the service is up. Deployment platforms (Render,
Docker healthchecks, load balancers) poll an endpoint like this to decide
whether an instance is ready to receive traffic.
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
