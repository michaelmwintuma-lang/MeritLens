"""Step 8 tests: the activity log records important actions, by day, and never anything a reporter does."""
import pytest
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.core.activity import ActivityEntry
from tests.conftest import login, recommendation


def log(client, **params):
    return client.get("/api/admin/activity", headers=login(client, "admin"), params=params).json()["entries"]


def actions(client):
    return [e["action"] for e in log(client)]


def test_sign_ins_and_failed_sign_ins_are_logged(client):
    login(client, "hr")
    client.post("/api/auth/login", json={"username": "hr", "password": "wrong"})
    client.post("/api/auth/login", json={"username": "nobody", "password": "wrong"})  # no such account: nothing to log
    entries = [e for e in log(client) if e["user"] == "Hana Reviewer"]
    assert {e["action"] for e in entries} == {"sign_in", "sign_in_failed"}
    assert all("nobody" not in e["details"] for e in log(client))


def test_only_the_day_is_kept_never_the_time(client):
    columns = {c["name"]: str(c["type"]) for c in inspect(engine).get_columns("activity_log")}
    assert set(columns) == {"id", "on_date", "user_id", "user_name", "action", "details"}
    assert columns["on_date"] == "DATE"
    login(client, "hr")
    assert len(log(client)[0]["date"]) == 10  # e.g. 2026-10-04


def test_account_changes_are_logged(client):
    admin = login(client, "admin")
    created = client.post("/api/admin/users", headers=admin, json={"username": "new.one", "full_name": "New One",
                                                                    "email": "new.one@example.org", "role": "employee"}).json()
    user_id = created["user"]["id"]
    client.patch(f"/api/admin/users/{user_id}", headers=admin, json={"full_name": "New Person"})
    client.post(f"/api/admin/users/{user_id}/reset-password", headers=admin)
    client.patch(f"/api/admin/users/{user_id}/active", headers=admin, json={"is_active": False})
    done = actions(client)
    for action in ["account_created", "account_edited", "password_reset", "account_deactivated"]:
        assert action in done
    assert created["temporary_password"] not in str(log(client))  # passwords are never logged


def test_nominations_and_decisions_are_logged(client):
    manager = login(client, "manager")
    member = client.get("/api/promotion/employees", headers=manager).json()["employees"][0]
    nomination = client.post("/api/promotion/nominations", headers=manager,
                             json=recommendation(member["id"])).json()
    client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"),
                json={"decision": "reject"})
    entries = {e["action"]: e for e in log(client)}
    assert entries["nomination_made"]["user"] == "Mo Manager" and member["full_name"] in entries["nomination_made"]["details"]
    assert entries["decision_made"]["user"] == "Hana Reviewer" and "rejected" in entries["decision_made"]["details"]


def test_nothing_a_reporter_does_is_logged(client):
    """Sending a report, replying, previewing and opening the case leave no trace in the activity log."""
    employee = login(client, "employee")  # the sign-in itself is logged, like everyone's
    with SessionLocal() as db:
        before = db.query(ActivityEntry).count()
    text = "My team lead keeps mocking my work in front of everyone during stand-ups."
    client.post("/api/reports/preview", headers=employee, json={"text": text})
    case = client.post("/api/reports", headers=employee, json={"category": "biased_rating", "text": text}).json()
    client.post("/api/reports/access", headers=employee, json={"case_id": case["case_id"], "key": case["key"]})
    client.post("/api/reports/messages", headers=employee, json={"case_id": case["case_id"], "key": case["key"], "text": "It happened again."})
    with SessionLocal() as db:
        assert db.query(ActivityEntry).count() == before


def test_hrs_actions_on_reports_are_logged_without_the_reporter(client):
    case = client.post("/api/reports", headers=login(client, "employee"),
                       json={"category": "biased_rating", "text": "My team lead keeps mocking my work in front of everyone."}).json()
    hr = login(client, "hr")
    client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=hr, json={"text": "Thank you, we are looking into it."})
    client.patch(f"/api/hr/reports/{case['case_id']}", headers=hr, json={"priority": "high"})
    hr_entries = [e for e in log(client) if e["action"] in ("report_replied", "report_updated")]
    assert {e["user"] for e in hr_entries} == {"Hana Reviewer"}
    assert all(case["case_id"] in e["details"] for e in hr_entries)
    assert not any("Eli Employee" in e["details"] or e["user"] == "Eli Employee" and e["action"] != "sign_in" for e in log(client))


def test_filtering_and_searching(client):
    login(client, "hr")
    login(client, "manager")
    assert {e["action"] for e in log(client, action="sign_in")} == {"sign_in"}
    assert {e["user"] for e in log(client, search="Mo Man")} == {"Mo Manager"}


@pytest.mark.parametrize("username", ["employee", "manager", "hr"])
def test_only_the_admin_reads_the_activity_log(client, username):
    assert client.get("/api/admin/activity", headers=login(client, username)).status_code == 403
