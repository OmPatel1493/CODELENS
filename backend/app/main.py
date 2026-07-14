"""FastAPI application entry point.

We use an application factory (`create_app`) rather than a module-level `app`
built inline. This makes the app configurable for tests (you can build an
instance with overridden settings) and is the pattern most FastAPI/Flask
production codebases follow.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.config import settings
from app.core.database import init_db


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

    # Allow the browser frontend (Vite dev server) to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Every route is mounted under /api so the frontend has a single, stable prefix.
    app.include_router(health.router, prefix="/api")

    return app


app = create_app()
