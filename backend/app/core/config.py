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
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR

    # --- Database ---
    # SQLite for the MVP; swap this one string for a Postgres URL later.
    DATABASE_URL: str = "sqlite:///./codelens.db"

    # --- CORS ---
    # Origins allowed to call the API from a browser (the Vite dev server).
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- Auth / JWT ---
    # DEV DEFAULT ONLY. Override with a long random value in production
    # (e.g. `openssl rand -hex 32`). A leaked secret lets anyone forge tokens.
    JWT_SECRET_KEY: str = "dev-insecure-secret-change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- Storage (repository archives, logs, reports, index snapshots) ---
    # "local" = filesystem (free, offline, the dev default).
    # "s3"    = AWS S3 / any S3-compatible store (set the AWS_* + S3_* vars).
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./data/storage"

    # Only used when STORAGE_BACKEND=s3.
    S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    # Custom endpoint for S3-compatible stores (e.g. MinIO). Blank = real AWS.
    S3_ENDPOINT_URL: str = ""

    # Guardrail: reject repository archives larger than this (bytes). Default 50 MB.
    MAX_ARCHIVE_BYTES: int = 50 * 1024 * 1024

    # --- Embeddings / vector index ---
    # Small, fast, CPU-friendly sentence-transformers model (384-dim, ~80 MB).
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    # How embeddings are computed:
    #   "local" = sentence-transformers on-box (torch). Free + offline, the dev
    #             default. Needs the optional `local` extra (`uv sync --extra local`).
    #   "api"   = a hosted embedding API over HTTP (no torch in the image), so the
    #             backend fits a small free host. Defaults to the Hugging Face
    #             Inference API serving the *same* model, so vectors match dev.
    EMBEDDING_BACKEND: str = "local"  # local | api
    # Override the embedding API endpoint (blank => HF Inference API for EMBEDDING_MODEL).
    EMBEDDING_API_URL: str = ""
    # Bearer token for the embedding API (a free HF read token for the default).
    HF_API_TOKEN: str = ""
    EMBEDDING_API_TIMEOUT: float = 60.0
    # Where the embedded ChromaDB index persists on disk.
    CHROMA_DIR: str = "./data/chroma"
    # Skip files bigger than this when parsing (bytes) — avoids huge/minified files.
    MAX_FILE_BYTES: int = 1024 * 1024
    # Only these extensions are parsed into chunks (source code, not assets).
    CODE_EXTENSIONS: list[str] = [
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rb",
        ".rs",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cs",
        ".php",
    ]

    # --- RAG answer layer (LLM synthesis over retrieval) ---
    # An OpenAI-compatible chat-completions endpoint. Default: Groq (free, fast).
    # Any OpenAI-compatible provider works by changing URL + model + key.
    LLM_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    # API key for the LLM. Blank => the /ask endpoint returns 503 (RAG disabled),
    # but search and bug-localization still work without it.
    LLM_API_KEY: str = ""
    LLM_TIMEOUT: float = 60.0
    # How many retrieved chunks to feed the model as grounding context.
    RAG_CONTEXT_CHUNKS: int = 6


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (built once per process)."""
    return Settings()


settings = get_settings()
