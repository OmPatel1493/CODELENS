# CodeLens

> **AI-powered codebase search & bug localization.** Index any repository, ask
> questions in plain English — *"where is JWT auth implemented?"* — and localize
> bugs directly from stack traces, with an explanation for every result.

CodeLens parses a repository into files, classes, and functions, embeds those code
chunks into a vector space, and serves semantic search and bug localization over a
clean REST API and a modern React interface.

---

## Features

- 🔎 **Semantic code search** — natural-language queries over a repository, ranked
  by meaning rather than keywords, with syntax-highlighted snippets and confidence
  scores.
- 🐞 **Bug localization** — paste a stack trace or error log and get the most
  likely source files, ranked and explained.
- 🧩 **Structural indexing** — files, directories, classes, functions, and imports
  extracted via tree-sitter for precise, language-aware chunking.
- 📊 **Repository insight** — statistics and an explorer for navigating an indexed
  codebase.
- 🔐 **Authenticated, multi-repo** — JWT auth with per-user repositories.

## Tech stack

| Layer          | Choice                                                       |
| -------------- | ------------------------------------------------------------ |
| Backend        | Python 3.12, FastAPI, SQLAlchemy, JWT                        |
| ML / Search    | sentence-transformers, FAISS, tree-sitter                   |
| Database       | PostgreSQL (SQLite for local development)                   |
| Frontend       | React, TypeScript, Vite, Tailwind CSS, shadcn/ui            |
| Infrastructure | Docker, GitHub Actions, Vercel (web), Render (API)          |

## Architecture

```
┌───────────┐      REST      ┌────────────────────────────┐
│  React /  │ ─────────────► │        FastAPI API         │
│   Vite    │ ◄───────────── │  api → services → models   │
└───────────┘      JSON      └──────────┬─────────┬────────┘
                                        │         │
                              metadata  │         │  vectors
                                        ▼         ▼
                                  ┌─────────┐ ┌────────┐
                                  │ Postgres│ │ FAISS  │
                                  │         │ │ index  │
                                  └─────────┘ └────────┘
```

A layered backend keeps concerns separate: routes handle HTTP, services hold
business logic, and models own persistence. Metadata lives in a relational
database; embeddings live in a FAISS vector index — each store used for what it
does best.

## Local development

Prerequisites: [`uv`](https://docs.astral.sh/uv/) (Python toolchain) and Node 20+.

```bash
# Backend
cd backend
uv sync                                  # create the virtualenv and install deps
uv run uvicorn app.main:app --reload     # API on http://localhost:8000
uv run pytest                            # run the test suite

# Interactive API docs → http://localhost:8000/docs
```

## Project layout

```
CodeLens/
├── backend/                FastAPI service
│   ├── app/
│   │   ├── api/routes/      HTTP endpoints
│   │   ├── core/            config, database
│   │   ├── models/          SQLAlchemy models
│   │   ├── schemas/         Pydantic request/response schemas
│   │   └── services/        business logic
│   └── tests/
└── frontend/               React + Vite application
```

## License

MIT
