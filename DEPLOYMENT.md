# Deploying CodeLens

Target topology: **frontend on Azure Static Web Apps**, **object storage on AWS S3**,
**database on Azure PostgreSQL**, and the **FastAPI backend on a host that can run
PyTorch**. This guide favors free tiers and is explicit about where "free" runs out.

> **The one honest caveat.** The backend bundles PyTorch + sentence-transformers +
> ChromaDB (~2 GB, needs ~1–2 GB RAM to embed). That does **not** fit Azure App
> Service **F1 (free)** or Render's 512 MB free tier. For a genuinely $0 backend,
> use **Hugging Face Spaces** (free CPU tier, built for ML). Azure App Service is
> the right home only on a **paid** plan (B1+) or with student credits.

---

## 0. Prerequisites

- Code pushed to GitHub (CI green).
- A strong secret: `openssl rand -hex 32` → use as `JWT_SECRET_KEY`.
- Accounts as needed: GitHub, AWS (for S3), Azure (for frontend/DB), Hugging Face
  (for the free backend).

## 1. AWS S3 (object storage) — free tier, 12 months

1. **Set a zero-spend budget alarm first** (Billing → Budgets → *Zero spend budget*).
2. Create an **IAM user** with a policy scoped to one bucket (`s3:PutObject`,
   `GetObject`, `DeleteObject`, `ListBucket`) and generate an access key.
3. Create a bucket `codelens-<you>` (Block Public Access = ON).
4. You'll set `STORAGE_BACKEND=s3`, `S3_BUCKET`, `AWS_REGION`,
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` on the backend host.

*(Staying on `STORAGE_BACKEND=local` is fine for a demo — but App Service / Spaces
disks are ephemeral, so uploads won't survive restarts. S3 is the durable choice.)*

## 2. Database — Azure Database for PostgreSQL (Flexible Server), free 12 months

1. Create a Flexible Server (Burstable **B1ms**, which the 12-month free grant
   covers), a database `codelens`, and add a firewall rule for your backend host
   (or "allow Azure services").
2. Connection string for the backend:
   ```
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/codelens?sslmode=require
   ```
   (SQLite still works for a quick demo — just leave `DATABASE_URL` unset.)

## 3. Backend

### Option A — Hugging Face Spaces (recommended, free, runs the ML stack)

1. Create a **Space** → SDK: **Docker**.
2. Point it at this repo's `backend/` (or push the backend with its `Dockerfile`).
   Spaces listens on port **7860**, so set the start command / `CMD` to
   `uvicorn app.main:app --host 0.0.0.0 --port 7860` (or add an `app_port` in the
   Space config).
3. Add **Secrets** in the Space settings: `JWT_SECRET_KEY`, `DATABASE_URL`,
   `CORS_ORIGINS` (your Static Web App URL), and the `S3_*` / `AWS_*` vars.
4. Your API base becomes `https://<user>-<space>.hf.space/api`.

### Option B — Azure App Service (paid B1+ / student credits)

1. Create a **Web App for Containers** (Linux, **B1** or higher — F1 can't run torch).
2. Deploy the `backend/Dockerfile` image (via GitHub Actions or `az webapp`).
3. Set the same env vars under **Configuration → Application settings**.

## 4. Frontend — Azure Static Web Apps (free)

1. Create a Static Web App linked to your GitHub repo. Build config:
   - **App location:** `frontend`
   - **Output location:** `dist`
   - Build command: `npm run build`
2. Set the build-time env var **`VITE_API_URL`** to your backend's `/api` URL
   (e.g. `https://<user>-<space>.hf.space/api`). Static Web Apps injects it at build.
3. Azure creates a GitHub Actions workflow to build & deploy on push.

## 5. Wire it together

On the **backend host**, set:

| Variable | Value |
| --- | --- |
| `JWT_SECRET_KEY` | output of `openssl rand -hex 32` |
| `CORS_ORIGINS` | `["https://<your-static-web-app-url>"]` |
| `DATABASE_URL` | Azure Postgres DSN (or unset for SQLite) |
| `STORAGE_BACKEND` | `s3` |
| `S3_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | from step 1 |
| `ENVIRONMENT` | `production` · `DEBUG=false` |

**CORS is the usual gotcha:** the backend must list the exact frontend origin, or
the browser blocks every request.

## 6. Verify

- `GET https://<backend>/api/health` → `{"status":"ok"}`
- `GET https://<backend>/api/health/db` → confirms the DB connection
- Open the Static Web App, register, add a repo, search — end to end.

## Cost summary ($0 path)

| Piece | Host | Cost |
| --- | --- | --- |
| Frontend | Azure Static Web Apps | Free |
| Backend (ML) | Hugging Face Spaces | Free CPU tier |
| Database | Azure PostgreSQL B1ms | Free 12 months (then paid) |
| Object storage | AWS S3 | Free 5 GB / 12 months (then pennies) |

Keep the AWS budget alarm on, and delete the Postgres server + S3 bucket when you're
done demoing so nothing bills after the free windows close.
