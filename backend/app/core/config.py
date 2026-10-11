"""
Settings, read from environment variables with safe defaults for local development.

Private settings (such as the Gmail app password) go in backend/.env, one NAME=value per line. That file is never
committed. A real environment variable always wins over the file.
"""
import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> None:
    """Read NAME=value lines from backend/.env into the environment (blank lines and # comments are skipped)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


if not os.getenv("SKIP_ENV_FILE"):  # tests set this, so they never pick up your private settings
    _load_env_file(BACKEND_DIR / ".env")

# Local files that must never be committed (database, signing key) live in backend/instance/
INSTANCE_DIR = BACKEND_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'app.db').as_posix()}")

# How long a login lasts before the user must sign in again
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "480"))

# Password for the fictional demo accounts created on first start
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")


def _load_secret_key() -> str:
    """Key that signs login tokens: APP_SECRET_KEY if set, otherwise generated once and kept in instance/secret.key."""
    if os.getenv("APP_SECRET_KEY"):
        return os.environ["APP_SECRET_KEY"]
    path = INSTANCE_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
    return path.read_text().strip()


SECRET_KEY = _load_secret_key()

# The product's name in emails and the API (the website's is in frontend/src/brand.js)
APP_NAME = os.getenv("APP_NAME", "MeritLens")

# Where the website is, for links in emails
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:5173")

# Mail server for welcome emails. Without SMTP_HOST, emails are saved in instance/outbox/ instead of sent.
SMTP = {
    "host": os.getenv("SMTP_HOST", ""),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "user": os.getenv("SMTP_USER", ""),
    # Gmail shows app passwords in groups ("abcd efgh ijkl mnop"); the spaces aren't part of it
    "password": os.getenv("SMTP_PASSWORD", "").replace(" ", ""),
    # Gmail only sends from the signed-in address, so by default the sender is that address
    "sender": os.getenv("SMTP_SENDER", "") or os.getenv("SMTP_USER", "") or "no-reply@meritlens.local",
    "sender_name": os.getenv("SMTP_SENDER_NAME", "") or APP_NAME,
}
# Where "Book a demo" requests are emailed (default: the Gmail address that sends the platform's emails)
DEMO_INBOX = os.getenv("DEMO_INBOX", "") or os.getenv("SMTP_USER", "")
OUTBOX_DIR = Path(os.getenv("OUTBOX_DIR", str(INSTANCE_DIR / "outbox")))
# Evidence employees attach to record-correction requests (PDF, JPEG, PNG). Never committed, never served directly:
# only through the feedback API, to the employee who sent it and to HR.
FEEDBACK_FILES_DIR = Path(os.getenv("FEEDBACK_FILES_DIR", str(INSTANCE_DIR / "correction_evidence")))
