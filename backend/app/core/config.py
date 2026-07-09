"""Application settings.

Loaded once at import time from environment variables (and a local .env file in
development). Centralizing config here means no module ever reads os.environ
directly — they import `settings`, which is typed and validated by Pydantic.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "CodeLens API"
    ENVIRONMENT: str = "development"  # development | production
    DEBUG: bool = True

    # --- Database ---
    # SQLite for the MVP; swap this one string for a Postgres URL later.
    DATABASE_URL: str = "sqlite:///./codelens.db"

    # --- CORS ---
    # Origins allowed to call the API from a browser (the Vite dev server).
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (built once per process)."""
    return Settings()


settings = get_settings()
