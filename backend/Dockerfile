# CodeLens backend image.
# Note: the ML stack (torch, sentence-transformers, chromadb) makes this image
# large (~2 GB). That's inherent to on-box embeddings — see DEPLOYMENT.md for
# free hosting options that can run it.

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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
