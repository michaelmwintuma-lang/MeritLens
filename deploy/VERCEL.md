# A preview online: the website on Vercel, the backend on Railway

```
Browser ──► https://your-app.vercel.app        Vercel: the website (React, built by Vite)
               │  /api/*  passed on by a Vercel rewrite (frontend/vercel.json)
               ▼
            https://your-backend.up.railway.app   Railway: the backend (Docker, always on)
               │  DATABASE_URL
               ▼
            PostgreSQL                             Railway's own database (or Neon / Supabase)
```

Why three parts: Vercel runs Python only as short functions of at most 250 MB, and the backend needs about 1 GB
(the model and its machine-learning libraries) and runs all the time (reminders, backups, explanations worked out
in the background). Vercel is ideal for the website, so it keeps that part.

Why the rewrite matters: the browser talks only to the Vercel address, and Vercel passes `/api/...` on to the
backend. The sign-in cookie (httpOnly, SameSite=Strict) therefore stays on one site and works; calling the backend
address directly from the website would break sign-in.

## 1. Put the project on GitHub

Vercel and Railway both deploy from a GitHub repository (private is fine).

## 2. The database and the backend on Railway

1. railway.com → New project → **Deploy from GitHub repo** → this repository. Railway reads `railway.json` and
   builds `deploy/backend.Dockerfile`.
2. In the same project: **+ New → Database → PostgreSQL**.
3. Backend service → **Variables**:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway fills it in; any `postgres://` address works) |
   | `APP_URL` | `https://your-app.vercel.app` (the Vercel address, from step 3; links in emails, secure cookies) |
   | `APP_SECRET_KEY` | a long random value: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `DEMO_PASSWORD` | the password of the starting accounts (`admin`, `hr`, `manager`…); not `demo1234` online |
   | `BACKUPS` | `0` (the container's disk is wiped on every deploy; Railway backs up the database) |
   | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`… | optional, as in `backend/.env.example`; without them emails go to an outbox |

4. Settings → **Networking → Generate domain**. Note the address, e.g. `meritlens-backend.up.railway.app`.
5. Give the service at least **1 GB of memory** (2 GB is comfortable). Check
   `https://<backend address>/api/health` answers `{"status":"ok"}`.

On first start the backend creates every table in PostgreSQL (migrations) and adds the demo accounts and 120 demo
employees. Updates apply new migrations by themselves; the data stays.

Files employees attach to correction requests are kept on the container's disk, so a redeploy loses them. That is
fine for a preview. To keep them, add a Railway **volume** mounted at `/app/backend/instance` and set
`RAILWAY_RUN_UID=0` (the volume belongs to root).

## 3. The website on Vercel

1. In `frontend/vercel.json`, replace `YOUR-BACKEND-ADDRESS` with the backend address from step 2.4 (no `https://`
   twice, no slash at the end), and push.
2. vercel.com → Add new project → this repository → **Root directory: `frontend`**. Vercel reads `vercel.json`
   (Vite, `npm run build`, output `dist`). No environment variables are needed.
3. Deploy, then put the Vercel address in the backend's `APP_URL` (step 2.3) if it changed.

Open the Vercel address and sign in as `admin` with your `DEMO_PASSWORD`. Then change the starting accounts'
passwords, or create real ones and deactivate those you don't need.

## Checking it works

From the project folder, run `python scripts/check_deployment.py https://your-app.vercel.app`. It asks for the
`DEMO_PASSWORD`, then checks through the website's address, as a browser does: the site loads, `/api` reaches the
backend, and each role signs in with a safe cookie, is recognised, and signs out. Each failure says what to fix.
By hand:

- `https://your-app.vercel.app/api/health` → `{"status":"ok"}` (the rewrite reaches the backend)
- Signing in keeps you signed in when you reload (the cookie works)
- Admin home page: the model is loaded, email status, no errors

## Instead of Railway

Render (a Docker web service; Standard plan for 2 GB), Fly.io or any server running
`deploy/backend.Dockerfile` work the same way: set the same variables, and point the rewrite at its address. The
database can be Neon or Supabase (free PostgreSQL): paste its connection string as `DATABASE_URL`.
