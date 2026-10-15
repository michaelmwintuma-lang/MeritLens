"""Shared test setup: every test runs against its own fresh, temporary database."""
import json
import os
import shutil
import tempfile
from pathlib import Path

# Point the app at a throwaway database BEFORE the app is imported, so tests never touch instance/app.db
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
# ...and at a copy of the live model and its results, so releasing a model in a test never changes the real ones
_backend = Path(__file__).resolve().parents[1]
_models, _results = Path(_tmp) / "models", Path(_tmp) / "results"
_models.mkdir()
for _name in ("model.joblib", "model_info.json", "background.csv"):
    if (_backend / "models" / _name).exists():
        shutil.copy2(_backend / "models" / _name, _models / _name)
shutil.copytree(_backend.parent / "results", _results)
os.environ["MODELS_DIR"], os.environ["RESULTS_DIR"] = str(_models), str(_results)
os.environ["MODEL_REGISTRY_DIR"] = str(_models / "registry")
os.environ["WARM_EXPLANATIONS"] = "0"  # no background LIME after every record edit in tests
os.environ["SCHEDULER"] = "0"          # no timer: tests run email retries, reminders and digests directly
os.environ["DEMO_PASSWORD"] = "demo1234"
os.environ["OUTBOX_DIR"] = os.path.join(_tmp, "outbox")   # welcome emails go to a temporary folder
os.environ["SMTP_HOST"] = ""                              # and are never sent during tests
os.environ["FEEDBACK_FILES_DIR"] = os.path.join(_tmp, "correction_evidence")
os.environ["PASSWORD_HASH_ITERATIONS"] = "1000"  # tests only: the app itself uses 200,000 rounds
os.environ["SKIP_ENV_FILE"] = "1"                          # never read your private backend/.env

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


from app.promotion.explain import version_of  # noqa: E402

_LIVE_VERSION = version_of(json.loads((_models / "model_info.json").read_text())) if (_models / "model_info.json").exists() else None


def restore_live_model():
    """Undo a test's model release: the original live model, its results, and only its entry in the registry."""
    from app.promotion.explain import reload_model
    registry = _models / "registry"
    if registry.exists():
        for folder in registry.iterdir():
            if folder.name != _LIVE_VERSION:
                shutil.rmtree(folder)
    info = _models / "model_info.json"
    if info.exists() and version_of(json.loads(info.read_text())) != _LIVE_VERSION:
        for name in ("model.joblib", "model_info.json", "background.csv"):
            shutil.copy2(_backend / "models" / name, _models / name)
        shutil.rmtree(_results)
        shutil.copytree(_backend.parent / "results", _results)
        reload_model()


@pytest.fixture
def client():
    """A test client on an empty database; start-up then adds the demo accounts (one per role)."""
    from app.core import jobs, throttle
    restore_live_model()
    jobs.clear()  # no background results carried over from another test
    throttle.clear()  # nor failed sign-ins counted against the test client's address
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


def login(client, username, password="demo1234"):
    """
    Sign in and return the Authorization header for later requests. The session cookie that sign-in also sets is
    dropped, so each request is made exactly as the header says (tests/test_sessions.py tests the cookie itself).
    """
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def wait_for_lime(client, employee_id, headers, seconds=60):
    """Start LIME for an employee (a background job) and wait for its result, as the page does."""
    import time
    res = client.post(f"/api/promotion/employees/{employee_id}/lime", headers=headers)
    deadline = time.monotonic() + seconds
    while res.status_code == 202 and time.monotonic() < deadline:
        time.sleep(0.1)
        res = client.get(f"/api/promotion/employees/{employee_id}/lime", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


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
