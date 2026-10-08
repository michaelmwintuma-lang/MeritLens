"""The compliance auditor: read-only oversight of decisions and the model, never reports or individual records."""
import pytest

from tests.conftest import login


def test_the_auditor_demo_account_signs_in(client):
    assert client.get("/api/auth/me", headers=login(client, "auditor")).json()["role"] == "auditor"


def test_the_auditor_reads_the_decision_log_and_the_model(client):
    auditor = login(client, "auditor")
    assert client.get("/api/promotion/decisions", headers=auditor).status_code == 200
    assert client.get("/api/promotion/importance", headers=auditor).status_code == 200


@pytest.mark.parametrize("method, path", [
    ("GET", "/api/promotion/employees"),            # no individual scores
    ("GET", "/api/promotion/nominations"),
    ("POST", "/api/promotion/nominations/1/decision"),
    ("GET", "/api/promotion/records/fields"),
    ("GET", "/api/hr/reports"),                     # never the reports
    ("GET", "/api/hr/reports/notifications"),
    ("POST", "/api/reports"),                       # and doesn't report through the system
    ("GET", "/api/admin/users"),
    ("GET", "/api/finance/pay-reviews"),
])
def test_the_auditor_cannot_see_reports_or_people_or_change_anything(client, method, path):
    res = client.request(method, path, headers=login(client, "auditor"), json={})
    assert res.status_code == 403, path


def test_an_existing_demo_database_gets_the_auditor_account_but_a_real_one_does_not(client):
    from app.accounts.models import User
    from app.accounts.seed import seed_demo_accounts
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        db.delete(db.query(User).filter_by(username="auditor").one())
        db.commit()
        seed_demo_accounts(db)  # a demo database made before the role existed
        assert db.query(User).filter_by(username="auditor").count() == 1

        db.delete(db.query(User).filter_by(username="auditor").one())
        db.query(User).filter_by(username="admin").one().email = "it@realcompany.com"
        db.commit()
        seed_demo_accounts(db)  # a real organisation's database: never given a demo login
        assert db.query(User).filter_by(username="auditor").count() == 0


def test_an_admin_can_create_an_auditor_account_but_not_link_it_to_an_employee(client):
    admin = login(client, "admin")
    body = {"username": "aud2", "full_name": "Second Auditor", "email": "aud2@example.org", "role": "auditor"}
    assert client.post("/api/admin/users", headers=admin, json=body).status_code == 201
    linked = client.post("/api/admin/users", headers=admin,
                         json=body | {"username": "aud3", "email": "aud3@example.org", "employee_id": 1})
    assert linked.status_code == 422
