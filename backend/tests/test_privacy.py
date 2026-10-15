"""
People's rights over their data: a copy of everything held about you; erasing someone who has left (their personal
data gone, decisions kept under a pseudonym, and they leave every list); and removal after the retention periods.
"""
import json
from datetime import datetime, timedelta

from sqlalchemy import select, update

from app.core.activity import ActivityEntry
from app.core.database import SessionLocal
from app.core.notifications import Notification
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.governance.models import EqualityMonitoring
from app.privacy import retention
from tests.conftest import login, recommendation


def own_record(client):
    return client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]


def leave_feedback(client):
    employee = login(client, "employee")
    client.post("/api/feedback/ratings", headers=employee, json={"clarity": 4, "usefulness": 3, "comment": "Mostly clear.", "flagged": []})
    client.post("/api/feedback/corrections", headers=employee, json={
        "field": "projects_completed", "requested_value": 9, "note": "My signed review form lists more projects."})


def test_everyone_can_download_everything_held_about_them(client):
    leave_feedback(client)
    res = client.get("/api/privacy/my-data", headers=login(client, "employee"))
    assert res.status_code == 200 and "attachment" in res.headers["content-disposition"]
    data = json.loads(res.text)
    assert data["account"]["username"] == "employee" and "password_hash" not in data["account"]
    assert data["employee_record"]["id"] == own_record(client) and data["employee_record"]["inputs"]
    assert len(data["explanation_ratings"]) == 1 and len(data["correction_requests"]) == 1
    assert "equality_monitoring" in data and "activity_log" in data
    # A role without an employee record gets their account part
    hr = json.loads(client.get("/api/privacy/my-data", headers=login(client, "hr")).text)
    assert hr["account"]["role"] == "hr" and "employee_record" not in hr


def test_hr_erases_someone_who_left_and_decisions_stay_under_a_pseudonym(client):
    person = own_record(client)
    leave_feedback(client)
    nomination = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(person)).json()["id"]
    hr = login(client, "hr")
    refused = client.post(f"/api/privacy/employees/{person}/erase", headers=hr, json={"reason": "Left the organisation."})
    assert refused.status_code == 409  # a nomination is still waiting
    client.post(f"/api/promotion/nominations/{nomination}/decision", headers=hr,
                json={"decision": "reject", "reason": "Not enough evidence of leadership in the new role yet."})

    for username in ("manager", "employee", "admin"):
        assert client.post(f"/api/privacy/employees/{person}/erase", headers=login(client, username),
                           json={"reason": "Left the organisation."}).status_code == 403
    res = client.post(f"/api/privacy/employees/{person}/erase", headers=hr, json={"reason": "Left the organisation on 30 June."})
    assert res.status_code == 200 and res.json()["pseudonym"] == f"Former employee no. {person}"

    with SessionLocal() as db:
        assert db.scalar(select(CorrectionRequest).where(CorrectionRequest.employee_id == person)) is None
        assert db.scalar(select(ExplanationRating).where(ExplanationRating.employee_id == person)) is None
        assert db.scalar(select(EqualityMonitoring).where(EqualityMonitoring.employee_id == person)) is None
    listed = client.get("/api/promotion/employees", headers=hr).json()["employees"]
    assert person not in {e["id"] for e in listed}
    assert client.get(f"/api/promotion/employees/{person}", headers=hr).status_code == 404
    [decision] = [d for d in client.get("/api/promotion/decisions", headers=hr).json() if d["employee"]["id"] == person]
    assert decision["employee"]["full_name"] == f"Former employee no. {person}" and decision["decision"] == "reject"
    assert client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"] is None
    assert client.get("/api/governance/audit/verify", headers=login(client, "auditor")).json()["intact"]


def test_old_personal_data_is_removed_after_its_retention_period(client):
    leave_feedback(client)
    client.post("/api/promotion/nominations", headers=login(client, "manager"),
                json=recommendation(client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"][1]["id"]))
    long_ago = datetime.now() - timedelta(days=4000)
    with SessionLocal() as db:
        db.execute(update(ExplanationRating).values(created_at=long_ago))
        db.execute(update(Notification).values(created_at=long_ago))
        db.execute(update(ActivityEntry).values(on_date=long_ago.date()))
        db.commit()
        removed = retention.run(db)
        assert removed["rating_comments"] == 1 and removed["notifications"] >= 1 and removed["activity_log"] >= 1
        rating = db.scalar(select(ExplanationRating))
        assert rating.comment is None and rating.clarity == 4  # the answers stay, for the totals
    assert client.get("/api/privacy/retention").json()["notifications"] == 180
