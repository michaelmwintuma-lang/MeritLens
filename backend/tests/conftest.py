"""Shared test setup: every test runs against its own fresh, temporary database."""
import os
import tempfile

# Point the app at a throwaway database BEFORE the app is imported, so tests never touch instance/app.db
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["DEMO_PASSWORD"] = "demo1234"
os.environ["OUTBOX_DIR"] = os.path.join(_tmp, "outbox")   # welcome emails go to a temporary folder
os.environ["SMTP_HOST"] = ""                              # and are never sent during tests
os.environ["EVIDENCE_DIR"] = os.path.join(_tmp, "evidence")  # report photos and videos too
os.environ["FEEDBACK_FILES_DIR"] = os.path.join(_tmp, "correction_evidence")
os.environ["SKIP_ENV_FILE"] = "1"                          # never read your private backend/.env

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """A test client on an empty database; start-up then adds the demo accounts (one per role)."""
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


def recommendation(employee_id, reason="Led the migration project and mentored two new colleagues this year.", **changes):
    """A complete, valid manager's recommendation (nomination) for one employee; override any field with changes."""
    from datetime import date, timedelta
    body = {
        "employee_id": employee_id,
        "proposed_title": "Senior Analyst",
        "proposed_start": (date.today() + timedelta(days=30)).isoformat(),
        "criteria": {key: {"rating": 4, "example": f"A clear example of strong {key} this year."}
                     for key in ("performance", "leadership", "skills", "impact")},
        "reason": reason,
        # Needed when the model doesn't recommend the person (most of the demo team); ignored otherwise
        "model_disagreement": "Strong client feedback and leadership that the data doesn't capture.",
        "proposed_raise": 8,
    }
    body.update(changes)
    return body


def sign_off(client, decision_id):
    """Finance signs off an approved promotion's pay rise (only then are the manager and employee told)."""
    res = client.post(f"/api/finance/pay-reviews/{decision_id}/sign-off", headers=login(client, "finance"), json={})
    assert res.status_code == 200, res.text
    return res.json()
