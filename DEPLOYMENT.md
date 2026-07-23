# Deploying CodeLens

The live demo runs **$0 and without a credit card**: the **FastAPI backend on
Render** (free Docker web service) and the **frontend on Cloudflare Pages**. Data is
ephemeral by default (SQLite + local storage); a durable upgrade (PostgreSQL + AWS S3)
is **config-only** — no code changes — and covered at the end.

> **Why not Hugging Face Spaces?** Earlier versions of this guide used HF Spaces
> (Docker SDK) as the free ML host. In **early July 2026 HF made Docker Spaces
> PRO-only ($9/mo)**, so it's no longer a $0 option. See ENGINEERING_NOTES §12.

> **How the free deploy fits.** The backend normally bundles PyTorch (~2 GB), which
> doesn't fit a 512 MB free host. So the deployed image sets **`EMBEDDING_BACKEND=api`**:
> embeddings are computed by a hosted Inference API instead of an on-box model, and
> `sentence-transformers`/torch is left out of the image (it lives in the optional
> `local` extra, used only for local dev). Result: a few-hundred-MB image that fits
> Render's free tier.

---

## 0. Prerequisites

- Code pushed to GitHub (CI green).
- A **free Hugging Face read token** for the embedding API:
  [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (role: Read).
- Accounts: GitHub, [Render](https://render.com), [Cloudflare](https://dash.cloudflare.com).
  (AWS + a Postgres provider only if you want the durable upgrade in §5.)

## 1. Backend — Render (free Docker web service)

The repo ships a **`render.yaml` Blueprint** at the root, so most of this is automatic.

1. In Render: **New → Blueprint** → connect your GitHub repo → select it. Render reads
   `render.yaml` and provisions a free Docker web service named `codelens-api`
   (`rootDir: backend`, health check `/api/health`, `EMBEDDING_BACKEND=api`,
   auto-generated `JWT_SECRET_KEY`).
2. Set the two secrets it asks for (marked `sync: false` in the Blueprint):
   - `HF_API_TOKEN` — your Hugging Face read token.
   - `CORS_ORIGINS` — leave as `["*"]` for now; tighten in §3 once the frontend exists.
3. Deploy. First build takes a few minutes. Your API is then live at
   `https://codelens-api.onrender.com` (Render shows the exact URL).
4. Verify: open `https://<your-api>.onrender.com/docs` (Swagger) and
   `GET /api/health` → `{"status":"ok"}`.

> **No `render.yaml`?** You can instead create the service by hand: New → Web Service →
> your repo → Root Directory `backend`, Runtime **Docker**, Instance **Free**, and add
> the env vars from the table in §4.

*(Alternative hosts that run the **full torch image** unchanged — Google Cloud Run,
Fly.io — work too, but require a credit card. See ENGINEERING_NOTES §12.)*

## 2. Frontend — Cloudflare Pages (free)

1. [Cloudflare dashboard](https://dash.cloudflare.com) → **Workers & Pages** →
   **Create** → **Pages** → **Connect to Git** → pick the repo.
2. Build settings:
   - Framework preset: **Vite**
   - **Root directory:** `frontend`
   - Build command: `npm run build` · Output directory: `dist`
3. Environment variable: **`VITE_API_URL`** = `https://<your-api>.onrender.com/api`
   (baked in at build time — the trailing `/api` matters).
4. Deploy → you get `https://<project>.pages.dev`. Copy it.

## 3. Wire CORS together

Back in Render → the service → **Environment**, set:

- `CORS_ORIGINS` = `["https://<project>.pages.dev"]`
  (**JSON array string** — brackets + quotes required, or the app crashes on boot).

Save; Render redeploys. **CORS is the usual gotcha:** the origin must match exactly,
with no trailing slash.

## 4. Backend environment variables

| Variable | Value |
| --- | --- |
| `EMBEDDING_BACKEND` | `api` (set by the Blueprint) |
| `HF_API_TOKEN` | free HF read token (embedding API auth) |
| `JWT_SECRET_KEY` | strong secret (Blueprint auto-generates; or `openssl rand -hex 32`) |
| `CORS_ORIGINS` | `["https://<your-pages-url>"]` (JSON array) |
| `ENVIRONMENT` | `production` · `DEBUG` = `false` |
| `DATABASE_URL` | *(optional)* Postgres DSN — unset ⇒ ephemeral SQLite |
| `STORAGE_BACKEND` | `local` (ephemeral) or `s3` (+ the `S3_*` / `AWS_*` vars) |

## 5. Verify end to end

- `GET https://<your-api>.onrender.com/api/health` → `{"status":"ok"}`
- Open the Pages site → register → add a small **public** GitHub repo → wait for
  `ready` → search. If requests are blocked, it's almost always `CORS_ORIGINS`.

> Free Render services **spin down after ~15 min idle** (~30–60 s cold start on the
> next request) and use **ephemeral disk** (SQLite + uploaded repos reset on redeploy).
> Expected for a demo. Click the link a minute before showing someone.

---

## Durable upgrade (optional) — Postgres + S3, config-only

Nothing below requires a code change — both are behind env-var-selected abstractions.

**Database → managed PostgreSQL.** Any free-tier Postgres (Render Postgres, Supabase,
Neon, Azure Database for PostgreSQL). Set:
```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/codelens?sslmode=require
```

**Object storage → AWS S3** (free tier: 5 GB / 12 months).
1. Set a **zero-spend budget alarm** first (Billing → Budgets).
2. Create an IAM user scoped to one bucket (`s3:PutObject/GetObject/DeleteObject/ListBucket`).
3. Bucket `codelens-<you>` (Block Public Access ON).
4. Set `STORAGE_BACKEND=s3`, `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY` on the backend.

## Cost summary ($0 path)

| Piece | Host | Cost |
| --- | --- | --- |
| Frontend | Cloudflare Pages | Free (forever) |
| Backend (slim, API embeddings) | Render free web service | Free (forever; sleeps when idle) |
| Embeddings | Hugging Face Inference API | Free (rate-limited) |
| Database | SQLite (ephemeral) | Free |
| Object storage | local filesystem (ephemeral) | Free |

The durable upgrade (Postgres + S3) may leave free tiers eventually; keep the AWS
budget alarm on and delete resources when you're done demoing.
