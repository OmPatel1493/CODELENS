"""FastAPI application entry point.

We use an application factory (`create_app`) rather than a module-level `app`
built inline. This makes the app configurable for tests (you can build an
instance with overridden settings) and is the pattern most FastAPI/Flask
production codebases follow.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, repositories
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging

configure_logging()
_access_log = logging.getLogger("codelens.access")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs once on startup. For the MVP we create tables here; production would
    # run Alembic migrations instead (see ENGINEERING_NOTES).
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Allow the browser frontend to call the API. Origins are configurable so the
    # deployed Static Web App URL can be added in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        _access_log.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    # Every route is mounted under /api so the frontend has a single, stable prefix.
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(repositories.router, prefix="/api")

    return app


app = create_app()
