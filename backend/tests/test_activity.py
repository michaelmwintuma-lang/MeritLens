"""Step 8 tests: the activity log records important actions, by day."""
import pytest
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine, is_sqlite
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


def test_filtering_and_searching(client):
    login(client, "hr")
    login(client, "manager")
    assert {e["action"] for e in log(client, action="sign_in")} == {"sign_in"}
    assert {e["user"] for e in log(client, search="Mo Man")} == {"Mo Manager"}


@pytest.mark.parametrize("username", ["employee", "manager", "hr"])
def test_only_the_admin_reads_the_activity_log(client, username):
    assert client.get("/api/admin/activity", headers=login(client, username)).status_code == 403


@pytest.mark.skipif(not is_sqlite(), reason="the old version's evidence folder sat next to its SQLite file")
def test_a_database_from_the_version_with_reporting_is_cleaned_up(client):
    """Anonymous reporting was removed: its tables, log entries and evidence folder go when the app starts."""
    from pathlib import Path
    from app.core.database import drop_removed_reporting
    evidence = Path(engine.url.database).parent / "evidence"  # beside the test database, never the real one
    with engine.begin() as connection:  # what the earlier version left behind
        connection.exec_driver_sql('CREATE TABLE reports (case_id TEXT PRIMARY KEY, text TEXT)')
        connection.exec_driver_sql('CREATE TABLE report_messages (case_id TEXT, number INTEGER)')
        connection.exec_driver_sql("INSERT INTO activity_log (on_date, user_name, action, details) "
                                   "VALUES ('2026-10-01', 'Hana Reviewer', 'report_replied', 'R-ABCD-EFGH')")
    evidence.mkdir(exist_ok=True)
    drop_removed_reporting()
    tables = inspect(engine).get_table_names()
    assert "reports" not in tables and "report_messages" not in tables
    with SessionLocal() as db:
        assert db.query(ActivityEntry).filter_by(action="report_replied").count() == 0
    assert not evidence.exists()
    # The activity log still opens (an unknown action would have broken it)
    assert client.get("/api/admin/activity", headers=login(client, "admin")).status_code == 200
