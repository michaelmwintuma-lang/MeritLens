"""
Email you can rely on: every email in the delivery log; a failed one tried again automatically and resendable; its
content dropped once delivered; the bell and the email from the same event; daily digests for people who choose
them (never for account emails); and reminders before things are late, each sent once.
"""
import smtplib
from datetime import date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.core import config, digests, mailer, reminders
from app.core.database import SessionLocal
from app.feedback.models import CorrectionRequest
from app.promotion.models import PayReview, ReviewCycle
from tests.conftest import emails_to, login, recommendation


def log(client, **params):
    return client.get("/api/admin/email/log", headers=login(client, "admin"), params=params).json()


def nominate(client, index=1):
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    res = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(team[index]["id"]))
    assert res.status_code == 201, res.text
    return res.json()["id"], team[index]


class FakeServer:
    """Stands in for smtplib.SMTP: accepts every email, or refuses all of them."""
    refuse = False
    sent: list = []

    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def starttls(self): pass
    def login(self, *args): pass

    def send_message(self, message):
        if FakeServer.refuse:
            raise OSError("connection refused")
        FakeServer.sent.append(message["To"])


@pytest.fixture
def mail_server(monkeypatch):
    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(smtplib, "SMTP", FakeServer)
    monkeypatch.setattr(mailer, "cannot_receive", lambda address: False)  # the demo accounts' example.org too
    FakeServer.refuse, FakeServer.sent = False, []
    return FakeServer


def test_every_email_is_logged_and_the_bell_gets_the_same_event(client):
    nominate(client)
    entries = log(client)["items"]
    [entry] = [e for e in entries if e["to"] == "hr@example.org"]
    assert entry["subject"].startswith("New nomination") and entry["status"] == "saved"  # no mail server in tests
    bell = client.get("/api/notifications", headers=login(client, "hr")).json()
    assert bell["unread"] == 1 and bell["items"][0]["text"].startswith("New nomination to review")
    assert bell["items"][0]["link"] == "/nominations"
    client.post("/api/notifications/read", headers=login(client, "hr"), json={})
    assert client.get("/api/notifications", headers=login(client, "hr")).json()["unread"] == 0
    # Only the admin reads the delivery log
    for username in ("hr", "manager", "auditor"):
        assert client.get("/api/admin/email/log", headers=login(client, username)).status_code == 403


def test_account_emails_go_to_the_log_but_not_the_bell(client):
    headers = login(client, "employee")
    client.post("/api/auth/change-password", headers=headers,
                json={"current_password": "demo1234", "new_password": "a-new-long-password-1"})
    assert any(e["subject"] == "Your password was changed" and e["kind"] == "security" for e in log(client)["items"])
    assert client.get("/api/notifications", headers=login(client, "employee", "a-new-long-password-1")).json()["unread"] == 0


def test_a_failed_email_is_tried_again_and_then_its_content_is_dropped(client, mail_server):
    mail_server.refuse = True
    nominate(client)
    [entry] = [e for e in log(client)["items"] if e["to"] == "hr@example.org"]
    assert entry["status"] == "failed" and entry["attempts"] == 1 and "couldn't be reached" in entry["last_error"]
    assert entry["next_attempt_at"] and entry["can_resend"]

    mail_server.refuse = False
    with SessionLocal() as db:  # the next attempt is due
        db.execute(update(mailer.EmailLog).where(mailer.EmailLog.id == entry["id"]).values(next_attempt_at=datetime(2000, 1, 1)))
        db.commit()
    assert mailer.retry_due() == 1
    [entry] = [e for e in log(client)["items"] if e["id"] == entry["id"]]
    assert entry["status"] == "sent" and entry["attempts"] == 2 and not entry["can_resend"]
    with SessionLocal() as db:
        assert db.get(mailer.EmailLog, entry["id"]).mail_json is None


def test_after_the_last_attempt_the_admin_can_resend(client, mail_server):
    mail_server.refuse = True
    nominate(client)
    [entry] = [e for e in log(client)["items"] if e["to"] == "hr@example.org"]
    for _ in mailer.RETRY_MINUTES:
        with SessionLocal() as db:
            db.execute(update(mailer.EmailLog).where(mailer.EmailLog.id == entry["id"]).values(next_attempt_at=datetime(2000, 1, 1)))
            db.commit()
        mailer.retry_due()
    [entry] = [e for e in log(client)["items"] if e["id"] == entry["id"]]
    assert entry["status"] == "gave_up" and entry["attempts"] == len(mailer.RETRY_MINUTES) + 1

    mail_server.refuse = False
    res = client.post(f"/api/admin/email/log/{entry['id']}/resend", headers=login(client, "admin"))
    assert res.status_code == 200 and res.json()["sent"]
    again = client.post(f"/api/admin/email/log/{entry['id']}/resend", headers=login(client, "admin"))
    assert again.status_code == 409  # delivered: its content is gone


def test_a_daily_digest_holds_routine_emails_but_never_account_ones(client, mail_server):
    assert client.put("/api/auth/preferences", headers=login(client, "hr"), json={"email_mode": "weekly"}).status_code == 422
    me = client.put("/api/auth/preferences", headers=login(client, "hr"), json={"email_mode": "daily"}).json()
    assert me["email_mode"] == "daily"
    nominate(client, 1)
    nominate(client, 2)
    held = log(client, status_filter="held")["items"]
    assert len(held) == 2 and all(e["to"] == "hr@example.org" for e in held)
    assert client.get("/api/notifications", headers=login(client, "hr")).json()["unread"] == 2  # the bell isn't held

    client.post("/api/auth/change-password", headers=login(client, "hr"),
                json={"current_password": "demo1234", "new_password": "a-new-long-password-1"})
    assert "hr@example.org" in mail_server.sent  # the security alert went at once

    with SessionLocal() as db:
        assert digests.send_due(db) == 1
    assert log(client, status_filter="held")["items"] == []
    assert len(log(client, status_filter="in_digest")["items"]) == 2
    assert mail_server.sent.count("hr@example.org") == 2  # the alert, then one digest


def test_managers_are_reminded_once_before_nominations_close(client):
    hr = login(client, "hr")
    # Give the manager someone the model recommends
    star = next(e for e in client.get("/api/promotion/employees", headers=hr).json()["employees"] if e["recommended"])
    mo = client.get("/api/auth/me", headers=login(client, "manager")).json()["id"]
    client.put("/api/promotion/teams/assign", headers=hr, json={"employee_ids": [star["id"]], "manager_user_id": mo})
    client.post("/api/promotion/cycles", headers=hr, json={"name": "2026 mid-year", "nominations_close": date.today().isoformat()})
    with SessionLocal() as db:
        sent = reminders.run_due(db)
        again = reminders.run_due(db)
    assert any("nominations for 2026 mid-year" in s for s in sent)
    [email] = [e for e in emails_to("manager@example.org") if "Nominations close today" in e["subject"]]
    assert star["full_name"] not in email["text"]  # a count only, never names
    assert not any("nominations" in s for s in again)


def test_finance_is_reminded_about_pay_rises_waiting_more_than_two_working_days(client):
    nomination, _ = nominate(client)
    res = client.post(f"/api/promotion/nominations/{nomination}/decision", headers=login(client, "hr"),
                      json={"decision": "approve", "reason": "Strong case for the promotion from the manager.", "approved_raise": 8})
    assert res.status_code == 201, res.text
    with SessionLocal() as db:
        assert not any("pay rise" in s for s in reminders.run_due(db))  # just arrived
        db.execute(update(PayReview).values(at=datetime.now() - timedelta(days=7)))
        db.commit()
        assert any("pay rise" in s for s in reminders.run_due(db))
        assert not any("pay rise" in s for s in reminders.run_due(db))  # once only
    assert any("waiting for sign-off" in e["subject"] for e in emails_to("finance@example.org"))


def test_hr_is_reminded_about_late_corrections_and_a_cycle_ready_to_close(client):
    employee = login(client, "employee")
    client.post("/api/feedback/corrections", headers=employee, json={
        "field": "projects_completed", "requested_value": 9, "note": "My signed review form lists more projects."})
    hr = login(client, "hr")
    client.post("/api/promotion/cycles", headers=hr, json={"name": "2026 mid-year", "nominations_close": date.today().isoformat()})
    with SessionLocal() as db:
        db.execute(update(CorrectionRequest).values(created_at=datetime.now() - timedelta(days=5)))
        db.execute(update(ReviewCycle).values(nominations_close=date.today() - timedelta(days=1)))
        db.commit()
        sent = reminders.run_due(db)
    assert any("correction" in s for s in sent) and any("ready to close" in s for s in sent)
    subjects = [e["subject"] for e in emails_to("hr@example.org")]
    assert any("record correction" in s for s in subjects) and any(s.startswith("Ready to close") for s in subjects)


def test_the_admin_can_run_reminders_now(client):
    res = client.post("/api/admin/email/reminders/run", headers=login(client, "admin"))
    assert res.status_code == 200 and isinstance(res.json()["sent"], list)
    assert client.post("/api/admin/email/reminders/run", headers=login(client, "hr")).status_code == 403


def test_working_days_skip_weekends():
    friday = date(2026, 10, 16)
    assert reminders.working_days_between(friday, friday + timedelta(days=3)) == 1  # to Monday
    assert reminders.working_days_between(friday, friday + timedelta(days=5)) == 3  # to Wednesday


class FakeBrevo:
    """Stands in for Brevo's email API: accepts every email, or answers with an error status."""
    status = 201
    message = ""
    bodies: list = []

    @staticmethod
    def post(url, json, headers, timeout):
        assert url == mailer.BREVO_URL and headers["api-key"] == "test-key"
        FakeBrevo.bodies.append(json)
        return httpx.Response(FakeBrevo.status, json={"message": FakeBrevo.message} if FakeBrevo.status >= 400 else {})


@pytest.fixture
def brevo(monkeypatch):
    monkeypatch.setattr(config, "BREVO_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", FakeBrevo.post)
    monkeypatch.setattr(mailer, "cannot_receive", lambda address: False)
    FakeBrevo.status, FakeBrevo.message, FakeBrevo.bodies = 201, "", []
    return FakeBrevo


def test_with_a_brevo_key_emails_go_through_its_api(client, brevo):
    status = client.get("/api/admin/email", headers=login(client, "admin")).json()
    assert status["configured"] and status["host"] == "api.brevo.com"
    nominate(client)
    [entry] = [e for e in log(client)["items"] if e["to"] == "hr@example.org"]
    assert entry["status"] == "sent"
    [body] = [b for b in brevo.bodies if b["to"] == [{"email": "hr@example.org"}]]
    assert body["subject"].startswith("New nomination") and body["htmlContent"].startswith("<!doctype html>")
    assert body["textContent"] and body["sender"]["email"]


def test_an_email_brevo_refuses_is_tried_again_with_its_reason(client, brevo):
    brevo.status, brevo.message = 400, "Sender not verified"
    nominate(client)
    [entry] = [e for e in log(client)["items"] if e["to"] == "hr@example.org"]
    assert entry["status"] == "failed" and "Sender not verified" in entry["last_error"]
    brevo.status, brevo.message = 401, "We have detected you are using an unrecognised IP address"
    with SessionLocal() as db:
        db.execute(update(mailer.EmailLog).where(mailer.EmailLog.id == entry["id"]).values(next_attempt_at=datetime(2000, 1, 1)))
        db.commit()
    mailer.retry_due()
    [entry] = [e for e in log(client)["items"] if e["id"] == entry["id"]]
    assert entry["last_error"] == "Brevo refused the API key (We have detected you are using an unrecognised IP address)"
