# CodeLens

> **AI-powered codebase search & bug localization.** Index any repository, ask
> questions in plain English — *"where is JWT auth implemented?"* — and localize
> bugs directly from stack traces, with an explanation for every result.

CodeLens parses a repository into files, classes, and functions, embeds those code
chunks into a vector space, and serves semantic search and bug localization over a
clean REST API and a modern React interface.

---

## Features

- **Semantic code search** — natural-language queries over a repository, ranked
  by meaning rather than keywords, with syntax-highlighted snippets and confidence
  scores.
- **AI answers (RAG)** — ask a question and get a concise natural-language answer
  *grounded* in the retrieved code, with inline `[n]` citations back to the exact
  files/symbols it used (retrieval stays the source of truth; the model only
  explains what the code says).
- **AI code review** — paste a diff or point at a public GitHub PR URL; CodeLens
  retrieves related code from the indexed repo as context and returns structured,
  severity-tagged review findings (so the review is informed by the *whole* codebase,
  not the diff in isolation).
- **Bug localization** — paste a stack trace or error log and get the most
  likely source files, ranked and explained.
- **Structural indexing** — files, directories, classes, functions, and imports
  extracted via tree-sitter for precise, language-aware chunking.
- **Repository insight** — statistics and an explorer for navigating an indexed
  codebase.
- **Authenticated, multi-repo** — JWT auth with per-user repositories.

## Tech stack

| Layer          | Choice                                                              |
| -------------- | ------------------------------------------------------------------- |
| Backend        | Python 3.12, FastAPI, SQLAlchemy, JWT                               |
| ML / Search    | sentence-transformers (on-box **or** hosted Inference API), ChromaDB (embedded), tree-sitter; RAG via any OpenAI-compatible LLM (Groq by default) |
| Database       | PostgreSQL in production (SQLite for local development)             |
| Object storage | AWS S3 — repository archives, logs, reports, exported indexes (local FS for dev) |
| Frontend       | React, TypeScript, Vite, Tailwind CSS, shadcn/ui                   |
| Infrastructure | Docker, GitHub Actions, Render (API), Vercel (web)                  |

> **Pluggable by design.** Two swap-by-env-var abstractions keep development at
> **$0/offline** while supporting real cloud in production: embeddings run either
> **on-box** (sentence-transformers) or via a **hosted Inference API** (slim image,
> free host), and blobs go to the **local filesystem** or **AWS S3**. The vector
> index runs embedded inside the API and is snapshotted to storage, so no separate
> vector-DB server is required.

## Architecture

```mermaid
flowchart TD
    U([Developer]) -->|browser| FE["React + Vite<br/>(Azure Static Web Apps)"]
    FE -->|REST / JSON| API["FastAPI backend<br/>api → services → models<br/>(Azure App Service)"]
    GH[(GitHub repo)] -->|clone / upload| API
    API -->|metadata| PG[("Azure PostgreSQL<br/>users · repos · chunks")]
    API -->|vectors| CH[("ChromaDB<br/>embedded index")]
    API -->|blobs| S3[("AWS S3<br/>archives · logs · reports · snapshots")]
    CH -. index snapshot .-> S3
```

A layered backend keeps concerns separate: routes handle HTTP, services hold
business logic, models own persistence. Each store is used for what it does best:
relational metadata in **Azure PostgreSQL**, semantic vectors in an **embedded
ChromaDB** index, and durable blobs (repository archives, logs, reports, and
exported index snapshots) in **AWS S3**. Compute and web hosting run on Azure;
object storage on AWS — a deliberate multi-cloud split.

## Local development

Prerequisites: [`uv`](https://docs.astral.sh/uv/) (Python toolchain) and Node 20+.

```bash
# Backend
cd backend
uv sync --extra local                    # venv + deps, incl. on-box embeddings (torch)
uv run uvicorn app.main:app --reload     # API on http://localhost:8000
uv run pytest                            # run the test suite

# `--extra local` installs sentence-transformers (torch) so embeddings run on-box
# (EMBEDDING_BACKEND=local, the default). Omit it for a slim install and set
# EMBEDDING_BACKEND=api + HF_API_TOKEN to embed via a hosted API instead. Tests
# need neither (embeddings are mocked).

# Interactive API docs → http://localhost:8000/docs
```

### With Docker (full stack)

```bash
docker compose up --build
# frontend → http://localhost:5173   |   API → http://localhost:8000/docs
```

Runs Postgres + backend + frontend together (mirrors production: slim, torch-free
backend using `EMBEDDING_BACKEND=api`). Set `HF_API_TOKEN` first — see the note at
the top of `docker-compose.yml`.

## Deployment

**Live demo:** [codelens-lilac.vercel.app](https://codelens-lilac.vercel.app)
*(free tier — the API sleeps when idle, so the first request may take ~30–60 s to wake).*

The live demo runs **$0, no credit card**: frontend on **Vercel**, backend on **Render**
(free Docker web service). The deploy image is slim because it uses
`EMBEDDING_BACKEND=api` (embeddings via a hosted Inference API) instead of bundling
PyTorch. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step instructions and honest
cost notes, including the durable upgrade (Postgres + S3, config-only).

## Continuous integration

Every push and PR runs [CI](.github/workflows/ci.yml): backend lint (ruff) + tests
(pytest) and a frontend type-check + build.

## Project layout

```
CodeLens/
├── backend/                FastAPI service
│   ├── app/
│   │   ├── api/routes/      HTTP endpoints
│   │   ├── core/            config, database, logging
│   │   ├── models/          SQLAlchemy models
│   │   ├── schemas/         Pydantic request/response schemas
│   │   └── services/        business logic (storage, ingestion, embeddings, search, …)
│   ├── tests/
│   └── Dockerfile
├── frontend/               React + Vite application (+ Dockerfile, nginx.conf)
├── .github/workflows/      CI (lint, test, build)
├── docker-compose.yml      local full stack
└── DEPLOYMENT.md           deploy guide (Azure + AWS S3)
```

## License

MIT
