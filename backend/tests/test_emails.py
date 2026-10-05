"""Emails: who gets which email, what it says, and that report alerts reveal nothing about the reporter."""
import pytest

from app.core import email_templates as templates
from app.core import mailer
from tests.conftest import emails_to, login, recommendation

HR_EMAIL, MANAGER_EMAIL, EMPLOYEE_EMAIL = "hr@example.org", "manager@example.org", "employee@example.org"
REPORT = "My supervisor threatened me after the meeting and said I would regret complaining. I feel unsafe."


def count(address):
    return len(emails_to(address))


# ─── Security alerts ──────────────────────────────────────────────────────────
def test_changing_your_password_sends_a_security_alert(client):
    before = count(EMPLOYEE_EMAIL)
    client.post("/api/auth/change-password", headers=login(client, "employee"),
                json={"current_password": "demo1234", "new_password": "a-new-password"})
    alert = emails_to(EMPLOYEE_EMAIL)[-1]
    assert count(EMPLOYEE_EMAIL) == before + 1 and alert["subject"] == "Your password was changed"
    assert "a-new-password" not in alert["text"]  # never the password itself


def test_changing_your_username_sends_old_and_new(client):
    client.post("/api/auth/change-username", headers=login(client, "manager"),
                json={"current_password": "demo1234", "new_username": "mo.m"})
    alert = emails_to(MANAGER_EMAIL)[-1]
    assert alert["subject"] == "Your username was changed" and "manager" in alert["text"] and "mo.m" in alert["text"]
    assert "You changed" in alert["text"]


def test_an_admin_renaming_you_sends_an_alert_too(client):
    hr_id = client.get("/api/auth/me", headers=login(client, "hr")).json()["id"]
    client.patch(f"/api/admin/users/{hr_id}", headers=login(client, "admin"), json={"username": "hana.r"})
    alert = emails_to(HR_EMAIL)[-1]
    assert "An administrator changed" in alert["text"] and "hana.r" in alert["text"]


# ─── Nominations and decisions ────────────────────────────────────────────────
def nominate(client):
    manager = login(client, "manager")
    me = client.get("/api/auth/me", headers=login(client, "employee")).json()  # the demo employee is on the team
    return client.post("/api/promotion/nominations", headers=manager,
                       json=recommendation(me["employee_id"])).json()


def test_hr_is_emailed_about_a_new_nomination(client):
    nominate(client)
    email = emails_to(HR_EMAIL)[-1]
    assert email["subject"].startswith("New nomination: ")
    assert "Mo Manager" in email["text"] and "/nominations" in email["text"]


def test_an_approval_emails_the_manager_and_the_employee(client):
    nomination = nominate(client)
    before_employee = count(EMPLOYEE_EMAIL)
    client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"),
                json={"decision": "approve", "reason": "Exceptional client feedback not in the data.", "approved_raise": 9})
    to_manager = emails_to(MANAGER_EMAIL)[-1]
    assert "Approved" in to_manager["text"] and "Exceptional client feedback" in to_manager["text"]
    assert count(EMPLOYEE_EMAIL) == before_employee + 1
    assert emails_to(EMPLOYEE_EMAIL)[-1]["subject"] == "Your promotion has been approved"


def test_a_rejection_emails_only_the_manager(client):
    nomination = nominate(client)
    before_employee = count(EMPLOYEE_EMAIL)
    client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"), json={"decision": "reject"})
    assert "Not approved" in emails_to(MANAGER_EMAIL)[-1]["text"]
    assert count(EMPLOYEE_EMAIL) == before_employee  # the employee isn't told of a rejection by email


# ─── Report alerts: nothing about the reporter, nothing of the text ───────────
def test_hr_gets_a_report_alert_without_the_text(client):
    case = client.post("/api/reports", headers=login(client, "employee"), json={"category": "harassment", "text": REPORT}).json()
    alert = emails_to(HR_EMAIL)[-1]
    assert alert["subject"] == "New anonymous report (high priority)"
    assert case["case_id"] in alert["text"] and "Harassment" in alert["text"]
    for leak in ["threatened", "supervisor", "unsafe", "Eli", "employee", case["key"]]:
        assert leak not in alert["text"] and leak not in alert["html"]


def test_the_reporter_gets_no_email_about_their_report(client):
    before = count(EMPLOYEE_EMAIL)
    client.post("/api/reports", headers=login(client, "employee"), json={"category": "bullying", "text": REPORT})
    assert count(EMPLOYEE_EMAIL) == before  # an email to the reporter would link them to the report


# ─── The admin's email page ───────────────────────────────────────────────────
def test_admin_sees_the_email_status_without_the_password(client):
    status = client.get("/api/admin/email", headers=login(client, "admin")).json()
    assert status["configured"] is False and "password" not in str(status).lower()


def test_admin_sends_a_test_email_and_sees_the_outbox(client):
    admin = login(client, "admin")
    res = client.post("/api/admin/email/test", headers=admin, json={"to": "someone@example.org"}).json()
    assert res["sent"] is False and "outbox" in res["detail"]
    latest = client.get("/api/admin/email/outbox", headers=admin).json()[0]
    assert latest["to"] == "someone@example.org" and latest["subject"].startswith("Test email")


@pytest.mark.parametrize("username", ["employee", "manager", "hr"])
def test_only_the_admin_uses_the_email_page(client, username):
    headers = login(client, username)
    assert client.get("/api/admin/email", headers=headers).status_code == 403
    assert client.post("/api/admin/email/test", headers=headers, json={"to": "a@example.org"}).status_code == 403
    assert client.get("/api/admin/email/outbox", headers=headers).status_code == 403


# ─── The emails themselves ────────────────────────────────────────────────────
def test_every_email_has_a_plain_and_a_branded_version():
    message = mailer.build("x@example.org", templates.welcome("Ada", "ada", "Temp-123"))
    assert message.get_body(("plain",)) is not None and message.get_body(("html",)) is not None
    assert "Promotion &amp; Reporting" in message.get_body(("html",)).get_content()
