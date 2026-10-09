"""The feedback dashboard (HR and auditor) and the admin's system health: real numbers, small-group protection."""
import json
from datetime import datetime, timedelta

import numpy as np
import pytest

from app.core.database import SessionLocal
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.promotion.drift import psi
from app.promotion.models import Decision, Employee
from app.reporting.models import Report
from tests.conftest import login


def dashboard(client, username="hr", **filters):
    return client.get("/api/feedback/dashboard", headers=login(client, username), params=filters)


def add_ratings(clarities, usefulness=5, flagged=(), department=None, version="v1", when=None):
    with SessionLocal() as db:
        query = db.query(Employee)
        if department:
            query = query.filter_by(department=department)
        people = query.limit(len(clarities)).all()
        for person, clarity in zip(people, clarities):
            db.add(ExplanationRating(employee_id=person.id, model_version=version, score=0.1, clarity=clarity,
                                     usefulness=usefulness, flagged_json=json.dumps(list(flagged)),
                                     created_at=when or datetime.utcnow()))
        db.commit()


@pytest.mark.parametrize("username, allowed", [("hr", True), ("auditor", True), ("manager", False), ("employee", False),
                                               ("admin", False), ("finance", False)])
def test_only_hr_and_the_auditor_see_the_feedback_dashboard(client, username, allowed):
    assert (dashboard(client, username).status_code == 200) == allowed
    res = client.get("/api/feedback/dashboard/export.csv", headers=login(client, username))
    assert (res.status_code == 200) == allowed


def test_clarity_and_usefulness_rates_need_at_least_five_ratings(client):
    add_ratings([5, 4, 1, 2])
    ratings = dashboard(client).json()["ratings"]
    assert ratings["count"] == 4 and ratings["clarity_rate"] is None and ratings["usefulness_rate"] is None
    add_ratings([4])
    ratings = dashboard(client).json()["ratings"]
    assert ratings["count"] == 5 and ratings["clarity_rate"] == 0.6 and ratings["usefulness_rate"] == 1.0


def test_contested_factors_are_sorted_and_small_counts_are_hidden(client):
    add_ratings([3] * 6, flagged=[{"feature": "late_days", "kind": "unfair"}])
    add_ratings([3], flagged=[{"feature": "manager_rating", "kind": "wrong"}])
    contested = dashboard(client).json()["ratings"]["contested"]
    assert [c["feature"] for c in contested] == ["late_days", "manager_rating"]
    assert contested[0]["unfair"] == 6 and contested[0]["share"] == round(6 / 7, 4)
    assert contested[1]["wrong"] == "<3"   # one person's mark can't be counted exactly


def test_correction_measures(client):
    with SessionLocal() as db:
        person = db.query(Employee).first()
        start = datetime(2026, 1, 1, 9)
        for status, hours in [("confirmed", 24), ("confirmed", 48), ("rejected", 12), ("pending", None)]:
            db.add(CorrectionRequest(employee_id=person.id, field="late_days", current_value=3, requested_value=1,
                                     note="Evidence in words.", status=status, created_at=start,
                                     decided_at=start + timedelta(hours=hours) if hours else None))
        db.commit()
    c = dashboard(client).json()["corrections"]
    assert (c["received"], c["confirmed"], c["rejected"], c["pending"]) == (4, 2, 1, 1)
    assert c["confirmation_rate"] == round(2 / 3, 4) and c["mean_resolution_hours"] == 28.0


def test_reports_are_counted_by_category_with_small_counts_hidden(client):
    employee = login(client, "employee")
    text = "My appraisal ignored two of my projects completely this year."
    for category in ["biased_rating"] * 3 + ["favouritism"]:
        client.post("/api/reports", headers=employee, json={"category": category, "text": text})
    counts = {c["category"]: c["count"] for c in dashboard(client).json()["reports"]["by_category"]}
    assert counts == {"biased_rating": 3, "favouritism": "<3", "discrimination": 0, "wrong_record": 0, "other_concern": 0}


def test_the_dashboard_never_shows_names_comments_or_report_texts(client):
    add_ratings([4] * 5, flagged=[{"feature": "late_days", "kind": "unfair"}])
    with SessionLocal() as db:
        db.query(ExplanationRating).update({"comment": "A private comment"})
        names = [e.full_name for e in db.query(Employee).limit(5)]
        db.commit()
    client.post("/api/reports", headers=login(client, "employee"),
                json={"category": "biased_rating", "text": "A private report text about my appraisal this year."})
    shown = dashboard(client, "auditor").text + client.get("/api/feedback/dashboard/export.csv", headers=login(client, "auditor")).text
    assert "private" not in shown and not any(name in shown for name in names)


def test_committee_override_rate_and_reasons(client):
    with SessionLocal() as db:
        person = db.query(Employee).first()
        for i, agrees in enumerate([True, True, False]):
            db.add(Decision(nomination_id=1000 + i, employee_id=person.id, decided_by=1, decision="approve",
                            model_score=0.1, model_threshold=0.23, model_recommended=agrees, agrees_with_model=agrees,
                            reason=None if agrees else "Strong client feedback the record doesn't show.",
                            model_version="v1"))
        db.commit()
    m = dashboard(client).json()["committee"]
    assert m["decisions"] == 3 and m["overrides"] == 1 and m["override_rate"] == round(1 / 3, 4)
    assert m["reasons"][0]["reason"] == "Strong client feedback the record doesn't show."


def test_filters_by_date_department_and_model_version(client):
    with SessionLocal() as db:
        departments = [d for (d,) in db.query(Employee.department).distinct()]
    add_ratings([5] * 5, department=departments[0], version="v-old", when=datetime(2025, 3, 1))
    add_ratings([1] * 5, department=departments[1], version="v-new", when=datetime(2026, 9, 1))
    assert dashboard(client, model_version="v-old").json()["ratings"]["clarity_rate"] == 1.0
    assert dashboard(client, department=departments[1]).json()["ratings"]["clarity_rate"] == 0.0
    assert dashboard(client, start="2026-01-01").json()["ratings"]["count"] == 5
    assert dashboard(client, end="2025-12-31").json()["ratings"]["count"] == 5
    assert dashboard(client, start="soon").status_code == 422


def test_departments_with_fewer_than_five_people_cant_be_chosen(client):
    with SessionLocal() as db:
        department = db.query(Employee.department).first()[0]
        people = db.query(Employee).filter_by(department=department).all()
        for person in people[4:]:
            person.department = "Elsewhere"  # leave exactly 4 people in it
        db.commit()
    options = dashboard(client).json()["options"]["departments"]
    assert department not in options
    assert dashboard(client, department=department).status_code == 422


def test_the_csv_export_has_the_same_numbers(client):
    add_ratings([5, 5, 4, 2, 1])
    csv = client.get("/api/feedback/dashboard/export.csv", headers=login(client, "hr")).text
    assert "ratings,clarity rate (4 or 5),0.6" in csv
    assert "corrections,confirmation rate,withheld (too few to show)" in csv


# ─── Drift ────────────────────────────────────────────────────────────────────
def test_psi_is_near_zero_for_the_same_distribution_and_large_for_a_shift():
    rng = np.random.default_rng(1)
    training = rng.normal(50, 10, 5000)
    assert psi(training, rng.normal(50, 10, 2000)) < 0.02
    assert psi(training, rng.normal(65, 10, 2000)) > 0.25


# ─── The admin's system health ────────────────────────────────────────────────
@pytest.mark.parametrize("username", ["hr", "manager", "employee", "finance", "auditor"])
def test_only_the_admin_sees_system_health(client, username):
    assert client.get("/api/admin/system", headers=login(client, username)).status_code == 403


def test_system_health_reports_the_live_system(client):
    data = client.get("/api/admin/system", headers=login(client, "admin")).json()
    assert data["accounts"]["by_role"] == {"employee": 1, "manager": 1, "hr": 1, "admin": 1, "finance": 1, "auditor": 1}
    from app.promotion.explain import get_model
    assert data["model"]["loaded"] and data["model"]["version"] == get_model().version and data["model"]["inputs"] == 20
    results = json.loads((__import__("pathlib").Path(__file__).resolve().parents[2] / "results" / "fairness.json").read_text())
    assert data["fairness"]["passes"] == results["passes"]
    assert data["drift"]["records"] == 120 and len(data["drift"]["inputs"]) == 20
    assert data["drift"]["status"] in ("stable", "moderate shift", "large shift")
    assert data["recent_activity"][0]["action"] == "Signed in"
    assert data["email"]["configured"] is False


def test_locked_accounts_are_counted(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "hr", "password": "nope"})
    assert client.get("/api/admin/system", headers=login(client, "admin")).json()["accounts"]["locked"] == 1


def test_drift_counts_only_what_chance_alone_cant_explain():
    from app.promotion.drift import drift_report
    from app.promotion.explain import get_model
    live = get_model()
    features = live.info["features"]
    same = live.background.sample(200, random_state=3)[features].to_dict("records")
    report = drift_report(live.background, same, features)
    assert len(report["shifted"]) <= 2 and all(r["chance_psi"] > 0 for r in report["inputs"])
    shifted = [r | {"training_hours_last_year": r["training_hours_last_year"] + 60} for r in same]
    report = drift_report(live.background, shifted, features)
    assert report["inputs"][0]["feature"] == "training_hours_last_year" and report["status"] == "large shift"
