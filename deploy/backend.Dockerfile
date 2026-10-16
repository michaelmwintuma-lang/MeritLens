# The API (FastAPI + the model). Built from the project folder:  docker compose -f deploy/docker-compose.yml build
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# pg_dump, for the nightly backups of the PostgreSQL database (app/core/backups.py)
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt

COPY backend/ ./
COPY results/ /app/results/
# Not as root. instance/ (secret key, evidence, backups) and the model registry are volumes
RUN useradd --create-home meritlens && mkdir -p instance models/registry \
    && chown -R meritlens /app
USER meritlens

EXPOSE 8000
# One worker: the timer (reminders, digests, backups) runs inside the app, and must run once. PORT is set by hosts
# such as Railway and Render; 8000 otherwise (docker compose).
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*' --no-access-log"]
