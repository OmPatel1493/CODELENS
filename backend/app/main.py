"""FastAPI application entry point.

We use an application factory (`create_app`) rather than a module-level `app`
built inline. This makes the app configurable for tests (you can build an
instance with overridden settings) and is the pattern most FastAPI/Flask
production codebases follow.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
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
