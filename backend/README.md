---
title: CodeLens API
emoji: 🔍
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# CodeLens API

FastAPI backend for [CodeLens](https://github.com/OmPatel1493/CODELENS) — AI-powered
codebase search & bug localization (tree-sitter chunking → sentence-transformers
embeddings → ChromaDB vector search, plus explainable bug localization).

This Space runs the container defined by `Dockerfile`. Interactive API docs live at
`/docs`; health check at `/api/health`.

**Config (Space → Settings → Variables and secrets):**

| Key | Notes |
| --- | --- |
| `JWT_SECRET_KEY` | **secret** — `openssl rand -hex 32` |
| `CORS_ORIGINS` | JSON array of allowed origins, e.g. `["https://codelens.pages.dev"]` |
| `DATABASE_URL` | optional — Postgres DSN; unset ⇒ SQLite (ephemeral on Spaces) |
| `STORAGE_BACKEND` | `local` (default, ephemeral) or `s3` (+ `S3_*` / `AWS_*`) |

The `sdk: docker` + `app_port: 8000` frontmatter above is what makes Spaces route
traffic to the port this app's Dockerfile exposes.
