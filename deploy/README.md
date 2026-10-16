# Deploying MeritLens on a server (Docker, HTTPS)

`python run.py` is for one computer. For real use, the files here run MeritLens on one Linux server with three
containers:

| Container | What it is |
|---|---|
| `db` | PostgreSQL 16 (the data, in a Docker volume) |
| `api` | the FastAPI backend and the model (one worker: the timer for reminders, digests and backups runs inside it) |
| `web` | Caddy: serves the website, passes `/api/` to the API, and gets and renews the **HTTPS certificate** by itself |

> **Status:** these files were written without Docker available, so they have not been run end to end. The CI
> builds both images and checks the API starts (`docker-images` job); try a full deployment on a test server first.

## What you need

- A Linux server (2 GB of memory is enough) with Docker and the Compose plugin.
- A domain name whose DNS points at the server, with ports 80 and 443 open (Caddy uses them for the certificate).

## Steps

1. Copy the project to the server (e.g. `git clone`).
2. Settings:

   ```bash
   cp deploy/.env.example deploy/.env
   nano deploy/.env        # DOMAIN, the passwords, BACKUP_PATH, email
   ```

   Generate each password and `APP_SECRET_KEY` with
   `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`.
3. The backup folder, writable by the API container's user (uid 1000):

   ```bash
   sudo mkdir -p /mnt/backups/meritlens && sudo chown 1000 /mnt/backups/meritlens
   ```

4. Start:

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
   ```

   The first start creates the tables, the starting accounts (`admin`, `hr`, … with `DEMO_PASSWORD`) and the demo
   employees. Open `https://<DOMAIN>`.
5. Sign in as `admin`, create the real accounts (each gets a temporary password by email), then deactivate the
   starting accounts you don't need. Replace the demo employees by importing your own (All employees → Import).
6. Optional, recommended: the promotion code's own restricted database role (`postgres/README.md`, steps 2 and 5):
   run `postgres/setup.sql`'s role part and `postgres/grants.sql` inside the `db` container, and set
   `PROMOTION_DATABASE_URL` in `deploy/.env`.

## Updating

```bash
git pull
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

The API brings the database up to date at start-up (migrations: `backend/migrations`).

## Backups

Every night the API writes a backup to `BACKUP_PATH` (database dump, correction evidence, model registry; see
`docs/BACKUPS.md`). Copy that folder off the server too. The Docker volumes `instance` (the secret key) and
`caddy-data` (certificates) are worth a copy as well; they can be made again, at the cost of everyone signing in
again or a new certificate.

## Security notes

- Caddy sends the security headers (Content-Security-Policy, HSTS, no framing) and redirects HTTP to HTTPS.
- Session cookies are `Secure` because `APP_URL` starts with `https://`.
- `REQUIRE_2FA_ROLES=hr,finance,admin` makes those roles use two-factor sign-in; `FOUR_EYES=1` makes a second HR
  person approve model releases and threshold-crossing corrections (needs two HR accounts).
- Only ports 80 and 443 are published; PostgreSQL and the API are reachable only inside the Docker network.
