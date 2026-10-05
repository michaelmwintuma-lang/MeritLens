"""Shared test setup: every test runs against its own fresh, temporary database."""
import os
import tempfile

# Point the app at a throwaway database BEFORE the app is imported, so tests never touch instance/app.db
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["DEMO_PASSWORD"] = "demo1234"
os.environ["OUTBOX_DIR"] = os.path.join(_tmp, "outbox")   # welcome emails go to a temporary folder
os.environ["SMTP_HOST"] = ""                              # and are never sent during tests
os.environ["SKIP_ENV_FILE"] = "1"                          # never read your private backend/.env

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """A test client on an empty database; start-up then adds the four demo accounts."""
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


def login(client, username, password="demo1234"):
    """Sign in and return the Authorization header for later requests."""
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def emails_to(address):
    """The emails saved in the test outbox for one address, oldest first: [{"subject", "text", "html", "reply_to"}]."""
    from email import message_from_bytes
    from email.policy import default
    from pathlib import Path

    outbox = Path(os.environ["OUTBOX_DIR"])
    found = []
    for path in sorted(outbox.glob("*.eml")) if outbox.exists() else []:
        message = message_from_bytes(path.read_bytes(), policy=default)
        if message["To"] == address:
            found.append({"subject": message["Subject"], "text": message.get_body(("plain",)).get_content(),
                          "html": message.get_body(("html",)).get_content(), "reply_to": message["Reply-To"]})
    return found
