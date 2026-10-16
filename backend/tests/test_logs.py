"""
Logging and error alerts (app/core/logs.py): every answer carries a request id; an unexpected error gets a short
message quoting it, is kept for the admin's page, and emails the admins at most once an hour per kind of error.
"""
import json
import logging

import pytest

from app.core import logs
from app.main import app
from tests.conftest import emails_to, login


@pytest.fixture
def broken_page():
    """A page that fails, as a bug would."""
    def boom():
        raise RuntimeError("the database went away")
    app.add_api_route("/api/test-broken", boom)
    yield "/api/test-broken"
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/api/test-broken"]


def test_every_answer_has_a_request_id(client):
    res = client.get("/api/health")
    assert len(res.headers["X-Request-ID"]) == 12
    assert client.get("/api/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    assert client.get("/api/health", headers={"X-Request-ID": "<script>"}).headers["X-Request-ID"] != "<script>"


def test_an_unexpected_error_is_reported_and_the_admins_are_alerted_once(client, broken_page):
    before = len(emails_to("admin@example.org"))
    res = client.get(broken_page)
    reference = res.headers["X-Request-ID"]
    assert res.status_code == 500 and reference in res.json()["detail"]
    assert "database went away" not in res.json()["detail"]  # no internals shown to the person
    [alert] = emails_to("admin@example.org")[before:]
    assert reference in alert["text"] and "RuntimeError" in alert["text"]

    client.get(broken_page)  # the same error again within the hour: logged, not emailed again
    assert len(emails_to("admin@example.org")) == before + 1
    errors = client.get("/api/admin/system", headers=login(client, "admin")).json()["errors"]
    assert len(errors) == 2 and errors[1]["reference"] == reference and errors[0]["where"] == f"GET {broken_page}"


def test_json_logs_are_one_object_per_line_without_query_strings():
    record = logging.makeLogRecord({"name": "meritlens.requests", "levelname": "INFO", "msg": "%s %s",
                                    "args": ("GET", "/api/health"), "path": "/api/health", "status": 200})
    entry = json.loads(logs.JsonFormatter().format(record))
    assert entry["message"] == "GET /api/health" and entry["status"] == 200 and entry["level"] == "INFO"


def test_a_failing_timer_step_alerts_the_admins(client):
    from app.core import scheduler
    def failing():
        raise ValueError("SMTP refused")
    scheduler._safely("daily digests", failing)
    assert [e for e in emails_to("admin@example.org") if "timer: daily digests" in e["subject"]]
