"""Deleting accounts, job titles on new accounts, and the full list of report categories with their minimums."""
import pytest

from app.reporting.routes import CATEGORIES
from app.reporting.triage import triage
from tests.conftest import emails_to, login, recommendation


def create(client, username="new.person", role="employee", **extra):
    return client.post("/api/admin/users", headers=login(client, "admin"), json={
        "username": username, "full_name": "New Person", "email": f"{username}@example.org", "role": role, **extra})


def user_id(client, username):
    return client.get("/api/auth/me", headers=login(client, username)).json()["id"]


# ─── Deleting accounts ────────────────────────────────────────────────────────
def test_admin_deletes_an_account_and_it_is_logged(client):
    new_id = create(client).json()["user"]["id"]
    admin = login(client, "admin")
    assert client.delete(f"/api/admin/users/{new_id}", headers=admin).status_code == 200
    assert all(u["id"] != new_id for u in client.get("/api/admin/users", headers=admin).json())
    entry = client.get("/api/admin/activity", headers=admin).json()["entries"][0]
    assert entry["action"] == "account_deleted" and "new.person" in entry["details"]


def test_a_deleted_account_can_no_longer_sign_in(client):
    created = create(client).json()
    client.delete(f"/api/admin/users/{created['user']['id']}", headers=login(client, "admin"))
    res = client.post("/api/auth/login", json={"username": "new.person", "password": created["temporary_password"]})
    assert res.status_code == 401


def test_you_cannot_delete_yourself(client):
    assert client.delete(f"/api/admin/users/{user_id(client, 'admin')}", headers=login(client, "admin")).status_code == 400


def test_accounts_in_the_decision_log_are_kept(client):
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(team[0]["id"]))
    res = client.delete(f"/api/admin/users/{user_id(client, 'manager')}", headers=login(client, "admin"))
    assert res.status_code == 409 and "Deactivate" in res.json()["detail"]


def test_deleting_a_manager_leaves_their_team_without_a_manager(client):
    admin = login(client, "admin")
    manager = create(client, "second.manager", role="manager").json()["user"]
    free = [e["id"] for e in client.get("/api/admin/employees", headers=admin).json() if e["manager_user_id"] is None][:2]
    client.put(f"/api/admin/users/{manager['id']}/team", headers=admin, json={"employee_ids": free})
    client.delete(f"/api/admin/users/{manager['id']}", headers=admin)
    directory = {e["id"]: e for e in client.get("/api/admin/employees", headers=admin).json()}
    assert all(directory[i]["manager_user_id"] is None for i in free)  # still in the directory, no manager


@pytest.mark.parametrize("username", ["employee", "manager", "hr"])
def test_only_the_admin_deletes_accounts(client, username):
    assert client.delete(f"/api/admin/users/{user_id(client, 'employee')}", headers=login(client, username)).status_code == 403


# ─── Job titles ───────────────────────────────────────────────────────────────
def test_the_admin_gives_a_job_title_when_creating_an_account(client):
    created = create(client, job_title="Payroll Officer").json()["user"]
    assert created["job_title"] == "Payroll Officer"
    assert "as Payroll Officer" in emails_to("new.person@example.org")[-1]["text"]
    edited = client.patch(f"/api/admin/users/{created['id']}", headers=login(client, "admin"), json={"job_title": "Senior Payroll Officer"})
    assert edited.json()["job_title"] == "Senior Payroll Officer"


def test_the_job_title_is_optional(client):
    assert create(client).json()["user"]["job_title"] is None


# ─── Report categories ────────────────────────────────────────────────────────
def test_the_form_offers_the_promotion_focused_categories(client):
    """Reporting is part of the feedback channel: new reports use the five promotion-focused categories."""
    groups = client.get("/api/reports/categories", headers=login(client, "employee")).json()
    labels = [item["label"] for group in groups for item in group["items"]]
    assert labels == ["Biased rating or appraisal", "Favouritism", "Discrimination", "Wrong or missing record",
                      "Other workplace concern"]


def test_reports_already_saved_keep_their_category(client):
    assert {"harassment", "discrimination", "bullying", "safety", "ethics", "other", "harm_risk"} <= set(CATEGORIES)
    assert CATEGORIES["bullying"] == "Bullying or intimidation"


def test_new_reports_cant_use_the_earlier_categories(client):
    res = client.post("/api/reports", headers=login(client, "employee"),
                      json={"category": "bullying", "text": "My team lead keeps mocking my work in front of everyone."})
    assert res.status_code == 422


@pytest.mark.parametrize("category,minimum", [("sexual_harassment", "high"), ("violence", "high"), ("harm_risk", "high"),
                                              ("retaliation", "medium"), ("substance", "medium"), ("theft", "low")])
def test_serious_categories_have_a_minimum_priority(category, minimum):
    assert triage("Something happened that I want to raise.", category)["priority"] == minimum


def test_a_risk_of_self_harm_is_still_high_priority_in_any_category(client):
    res = client.post("/api/reports", headers=login(client, "employee"),
                      json={"category": "other_concern", "text": "A colleague keeps saying they don't see the point in going on."})
    assert res.status_code == 201
    assert emails_to("hr@example.org")[-1]["subject"] == "New anonymous report (high priority)"
