# CodeLens API (backend)

FastAPI service for [CodeLens](https://github.com/OmPatel1493/CODELENS) — AI-powered
codebase search & bug localization. Layered `api → services → models`; see the root
`README.md` for the full picture and `../DEPLOYMENT.md` for deploying.

## Run locally

```bash
uv sync --extra local                 # deps incl. on-box embeddings (torch)
uv run uvicorn app.main:app --reload  # http://localhost:8000  (docs at /docs)
uv run pytest                         # test suite (embeddings mocked — no torch needed)
```

## Embeddings backend

Selected by `EMBEDDING_BACKEND`:

- `local` (default) — sentence-transformers on-box. Free/offline; needs the `local`
  extra (`uv sync --extra local`, pulls torch).
- `api` — a hosted embedding API over HTTP (no torch). Used for the slim free deploy;
  set `HF_API_TOKEN`. Defaults to the HF Inference API for the same model.

See `.env.example` for all settings and `../ENGINEERING_NOTES.md` §12 for the why.
