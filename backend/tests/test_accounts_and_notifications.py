"""Tests for welcome emails, editing accounts, changing your username, notifications, and the public summary."""
from app.core.config import APP_NAME
import pytest

from tests.conftest import emails_to, login


def create(client, username="new.person", email="new.person@example.org", role="employee"):
    return client.post("/api/admin/users", headers=login(client, "admin"),
                       json={"username": username, "full_name": "New Person", "email": email, "role": role})


def test_the_first_time_guide_can_be_closed_and_shown_again(client):
    headers = login(client, "manager")
    assert client.get("/api/auth/me", headers=headers).json()["guide_done"] is False
    assert client.put("/api/auth/guide", headers=headers, json={"done": True}).json()["guide_done"] is True
    assert client.get("/api/auth/me", headers=headers).json()["guide_done"] is True
    assert client.put("/api/auth/guide", headers=headers, json={"done": False}).json()["guide_done"] is False


# ─── Welcome emails ───────────────────────────────────────────────────────────
def test_new_accounts_get_a_welcome_email_with_their_sign_in_details(client):
    res = create(client)
    assert res.status_code == 201
    body = res.json()
    assert body["email_sent"] is False and "saved to instance/outbox/" in body["email_detail"]  # no mail server in tests
    email = emails_to("new.person@example.org")[-1]
    assert email["subject"] == f"Your {APP_NAME} account"
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


# ─── Public summary for the landing page ──────────────────────────────────────
def test_the_landing_page_summary_needs_no_sign_in_and_reveals_no_one(client):
    res = client.get("/api/public/summary")
    assert res.status_code == 200
    assert set(res.json()) <= {"trained", "model", "inputs", "threshold", "roc_auc", "pr_auc", "pr_auc_baseline",
                               "test_size", "fairness_passes", "lowest_fairness_ratio"}


def test_the_landing_page_numbers_are_the_measured_ones(client):
    """Review B2, B3: the website showed hard-coded numbers (0.93, 79%)."""
    import json
    from pathlib import Path
    results = Path(__file__).resolve().parents[2] / "results"
    facts = client.get("/api/public/summary").json()
    metrics = json.loads((results / "metrics.json").read_text())
    assert facts["roc_auc"] == metrics["roc_auc"] and facts["threshold"] == metrics["threshold"]
    assert facts["inputs"] == 20


def test_the_website_shows_no_made_up_numbers():
    from pathlib import Path
    pages = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "public"
    text = "".join(p.read_text(encoding="utf-8") for p in pages.glob("*.jsx"))
    for invented in ['"0.93"', '"93%"', '"20,000"', "79%", "87%", "14 of 14", "21 performance"]:
        assert invented not in text, invented
