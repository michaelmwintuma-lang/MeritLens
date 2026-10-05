"""Tests for welcome emails, editing accounts, changing your username, notifications, and the public summary."""
import pytest

from tests.conftest import emails_to, login


def create(client, username="new.person", email="new.person@example.org", role="employee"):
    return client.post("/api/admin/users", headers=login(client, "admin"),
                       json={"username": username, "full_name": "New Person", "email": email, "role": role})


# ─── Welcome emails ───────────────────────────────────────────────────────────
def test_new_accounts_get_a_welcome_email_with_their_sign_in_details(client):
    res = create(client)
    assert res.status_code == 201
    body = res.json()
    assert body["email_sent"] is False and "saved to instance/outbox/" in body["email_detail"]  # no mail server in tests
    email = emails_to("new.person@example.org")[-1]
    assert email["subject"] == "Your account for the Promotion & Reporting platform"
    assert "new.person" in email["text"] and body["temporary_password"] in email["text"] and "/login" in email["text"]
    assert body["temporary_password"] in email["html"]  # the branded version carries the same details


def test_an_email_address_is_required_and_must_be_unique(client):
    admin = login(client, "admin")
    no_email = {"username": "x.y", "full_name": "X Y", "role": "employee"}
    assert client.post("/api/admin/users", headers=admin, json=no_email).status_code == 422
    assert create(client, email="not-an-email").status_code == 422
    assert create(client, username="other.person", email="hr@example.org").status_code == 409  # the demo HR's address


def test_a_password_reset_is_emailed_too(client):
    user_id = create(client).json()["user"]["id"]
    res = client.post(f"/api/admin/users/{user_id}/reset-password", headers=login(client, "admin")).json()
    email = emails_to("new.person@example.org")[-1]
    assert email["subject"] == "Your new temporary password" and res["temporary_password"] in email["text"]


# ─── The admin edits accounts ─────────────────────────────────────────────────
def test_admin_changes_a_username_and_the_person_signs_in_with_it(client):
    created = create(client).json()
    res = client.patch(f"/api/admin/users/{created['user']['id']}", headers=login(client, "admin"),
                       json={"username": "renamed.person", "full_name": "Renamed Person"})
    assert res.status_code == 200 and res.json()["username"] == "renamed.person"
    login(client, "renamed.person", created["temporary_password"])


def test_edits_keep_usernames_unique_and_only_the_admin_can_edit(client):
    user_id = create(client).json()["user"]["id"]
    assert client.patch(f"/api/admin/users/{user_id}", headers=login(client, "admin"), json={"username": "hr"}).status_code == 409
    assert client.patch(f"/api/admin/users/{user_id}", headers=login(client, "hr"), json={"full_name": "Hacked"}).status_code == 403


# ─── People change their own username ─────────────────────────────────────────
def test_changing_your_username_needs_your_password(client):
    headers = login(client, "manager")
    assert client.post("/api/auth/change-username", headers=headers, json={"current_password": "wrong", "new_username": "mo.m"}).status_code == 400
    assert client.post("/api/auth/change-username", headers=headers, json={"current_password": "demo1234", "new_username": "hr"}).status_code == 409
    assert client.post("/api/auth/change-username", headers=headers, json={"current_password": "demo1234", "new_username": "mo.m"}).json()["username"] == "mo.m"
    login(client, "mo.m")


# ─── Notifications ────────────────────────────────────────────────────────────
TEXT = "He threatened me in the car park after the meeting and I feel unsafe at work."


def report(client):
    return client.post("/api/reports", headers=login(client, "employee"), json={"category": "other", "text": TEXT}).json()


def test_hr_is_notified_of_new_reports_and_replies(client):
    hr = login(client, "hr")
    case = report(client)
    first = client.get("/api/hr/reports/notifications", headers=hr).json()
    assert first == [{"case_id": case["case_id"], "kind": "new_report", "priority": "high", "text": first[0]["text"]}]
    client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=hr, json={"text": "Thank you, we are on it."})
    assert client.get("/api/hr/reports/notifications", headers=hr).json() == []  # answered
    client.post("/api/reports/messages", headers=login(client, "employee"),
                json={"case_id": case["case_id"], "key": case["key"], "text": "It happened again today."})
    assert client.get("/api/hr/reports/notifications", headers=hr).json()[0]["kind"] == "reporter_replied"


def test_hr_notifications_hold_nothing_about_the_reporter(client):
    report(client)
    item = client.get("/api/hr/reports/notifications", headers=login(client, "hr")).json()[0]
    assert set(item) == {"case_id", "kind", "priority", "text"}  # no names, accounts or times


def test_reporters_check_their_saved_cases_for_replies(client):
    case = report(client)
    client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=login(client, "hr"), json={"text": "Can you tell us more?"})
    res = client.post("/api/reports/updates", headers=login(client, "employee"),
                      json={"cases": [{"case_id": case["case_id"], "key": case["key"]},
                                      {"case_id": "R-AAAA-AAAA", "key": "AAAA-AAAA-AAAA-AAAA"}]}).json()
    assert res == [{"case_id": case["case_id"], "status": "investigating", "messages": 1, "investigator_wrote_last": True}]


@pytest.mark.parametrize("username", ["employee", "manager", "admin"])
def test_only_hr_gets_hr_notifications(client, username):
    assert client.get("/api/hr/reports/notifications", headers=login(client, username)).status_code == 403


# ─── Public summary for the landing page ──────────────────────────────────────
def test_the_landing_page_summary_needs_no_sign_in_and_reveals_no_one(client):
    res = client.get("/api/public/summary")
    assert res.status_code == 200
    assert set(res.json()) <= {"trained", "model", "roc_auc", "pr_auc", "pr_auc_baseline", "test_size",
                               "fairness_passes", "lowest_fairness_ratio"}
