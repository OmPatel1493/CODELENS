# CodeLens backend image.
# Slim by design: the default dependency set has NO torch (sentence-transformers
# lives in the optional `local` extra, not installed here). The deployed backend
# runs EMBEDDING_BACKEND=api, so this image is a few hundred MB and fits small
# free hosts (e.g. Render). See DEPLOYMENT.md and ENGINEERING_NOTES §11.

FROM python:3.12-slim

# uv for fast, reproducible installs (copied from the official uv image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Dependency layer — cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Application code.
COPY app ./app

ENV ENVIRONMENT=production \
    DEBUG=false

EXPOSE 8000
# Bind the platform-provided $PORT (Render/most PaaS inject it); default 8000 for
# local runs and docker-compose. Shell form so ${PORT} is expanded at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
