"""Managers' structured recommendations, and promotion pay rises: within HR's policy, decided by HR, seen only by the
right people, and kept away from the model."""
from datetime import date, timedelta

import pytest

from app.promotion.features import MODEL_FEATURES
from tests.conftest import emails_to, login, recommendation, sign_off


def team(client):
    return client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]


def recommend(client, employee_id, **changes):
    return client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(employee_id, **changes))


def decide(client, nomination_id, **body):
    return client.post(f"/api/promotion/nominations/{nomination_id}/decision", headers=login(client, "hr"),
                       json={"decision": "approve", "reason": "Strong evidence from the manager beyond the data.", **body})


def member(client):
    return next(e for e in team(client) if not e["recommended"])  # the demo team are all below the threshold


# ─── The manager's recommendation ─────────────────────────────────────────────
def test_hr_sees_the_whole_recommendation(client):
    nomination_id = recommend(client, member(client)["id"]).json()["id"]
    rec = client.get(f"/api/promotion/nominations/{nomination_id}", headers=login(client, "hr")).json()["recommendation"]
    assert rec["proposed_title"] == "Senior Analyst" and rec["proposed_raise"] == 8
    assert [c["key"] for c in rec["criteria"]] == ["performance", "leadership", "skills", "impact"]
    assert rec["criteria"][0]["rating"] == 4 and rec["model_recommended_then"] is False and rec["model_disagreement"]


def test_every_criterion_needs_a_rating_and_an_example(client):
    employee_id = member(client)["id"]
    partial = recommendation(employee_id)
    del partial["criteria"]["impact"]
    assert client.post("/api/promotion/nominations", headers=login(client, "manager"), json=partial).status_code == 422
    too_vague = recommendation(employee_id)
    too_vague["criteria"]["skills"] = {"rating": 4, "example": "good"}
    assert client.post("/api/promotion/nominations", headers=login(client, "manager"), json=too_vague).status_code == 422
    off_scale = recommendation(employee_id)
    off_scale["criteria"]["skills"] = {"rating": 6, "example": "Certified in two new tools this year."}
    assert client.post("/api/promotion/nominations", headers=login(client, "manager"), json=off_scale).status_code == 422


def test_disagreeing_with_the_model_needs_a_reason_from_the_manager_too(client):
    employee_id = member(client)["id"]
    assert recommend(client, employee_id, model_disagreement=None).status_code == 422
    assert recommend(client, employee_id, model_disagreement="Good work").status_code == 422  # under 20 characters
    assert recommend(client, employee_id).status_code == 201


def test_the_start_date_must_be_within_the_next_year(client):
    employee_id = member(client)["id"]
    assert recommend(client, employee_id, proposed_start=(date.today() - timedelta(days=1)).isoformat()).status_code == 422
    assert recommend(client, employee_id, proposed_start=(date.today() + timedelta(days=400)).isoformat()).status_code == 422


# ─── The pay policy ───────────────────────────────────────────────────────────
def test_managers_propose_within_hrs_pay_policy(client):
    employee_id = member(client)["id"]
    assert client.get("/api/promotion/pay-policy", headers=login(client, "manager")).json() == {"min_raise": 5.0, "max_raise": 15.0}
    assert recommend(client, employee_id, proposed_raise=20).status_code == 422
    assert recommend(client, employee_id, proposed_raise=3).status_code == 422
    assert recommend(client, employee_id, proposed_raise=15).status_code == 201


def test_only_hr_changes_the_pay_policy_and_it_is_logged(client):
    assert client.put("/api/promotion/pay-policy", headers=login(client, "manager"), json={"min_raise": 1, "max_raise": 50}).status_code == 403
    hr = login(client, "hr")
    assert client.put("/api/promotion/pay-policy", headers=hr, json={"min_raise": 10, "max_raise": 5}).status_code == 422
    assert client.put("/api/promotion/pay-policy", headers=hr, json={"min_raise": 3, "max_raise": 12}).json()["max_raise"] == 12
    actions = [e["action"] for e in client.get("/api/admin/activity", headers=login(client, "admin")).json()["entries"]]
    assert "pay_policy_changed" in actions


# ─── HR's decision on pay ─────────────────────────────────────────────────────
def test_an_approval_needs_a_pay_rise(client):
    nomination_id = recommend(client, member(client)["id"]).json()["id"]
    assert decide(client, nomination_id).status_code == 422
    entry = decide(client, nomination_id, approved_raise=10).json()
    assert entry["approved_raise"] == 10 and entry["proposed_raise"] == 8 and entry["proposed_title"] == "Senior Analyst"


def test_going_outside_the_policy_needs_a_reason(client):
    nomination_id = recommend(client, member(client)["id"]).json()["id"]
    assert decide(client, nomination_id, approved_raise=20).status_code == 422
    assert decide(client, nomination_id, approved_raise=20, raise_reason="Matching an outside offer, approved by the director.").status_code == 201


def test_a_rejection_records_no_pay_rise(client):
    nomination_id = recommend(client, member(client)["id"]).json()["id"]
    res = client.post(f"/api/promotion/nominations/{nomination_id}/decision", headers=login(client, "hr"),
                      json={"decision": "reject", "approved_raise": 12})
    assert res.status_code == 201 and res.json()["approved_raise"] is None


# ─── Who sees the pay rise ────────────────────────────────────────────────────
def test_the_employee_sees_only_their_approved_promotion(client):
    me = client.get("/api/auth/me", headers=login(client, "employee")).json()
    employee = login(client, "employee")
    nomination_id = recommend(client, me["employee_id"]).json()["id"]
    assert client.get("/api/promotion/my-promotions", headers=employee).json() == []  # pending: not shown yet
    decision = decide(client, nomination_id, approved_raise=11).json()
    assert client.get("/api/promotion/my-promotions", headers=employee).json() == []  # waiting for Finance: not yet
    sign_off(client, decision["id"])
    mine = client.get("/api/promotion/my-promotions", headers=employee).json()
    assert mine[0]["title"] == "Senior Analyst" and mine[0]["raise"] == 11 and mine[0]["start"]
    email = emails_to("employee@example.org")[-1]
    assert email["subject"] == "Your promotion has been approved" and "11%" in email["text"] and "Senior Analyst" in email["text"]


@pytest.mark.parametrize("username", ["manager", "hr", "admin"])
def test_only_employees_use_my_promotions(client, username):
    assert client.get("/api/promotion/my-promotions", headers=login(client, username)).status_code == 403


def test_the_manager_hears_the_approved_rise(client):
    nomination_id = recommend(client, member(client)["id"]).json()["id"]
    sign_off(client, decide(client, nomination_id, approved_raise=9.5).json()["id"])
    assert "9.5%" in emails_to("manager@example.org")[-1]["text"]


# ─── Pay never reaches the model ──────────────────────────────────────────────
def test_pay_is_not_a_model_input():
    assert not [f for f in MODEL_FEATURES if any(word in f for word in ("salary", "raise", "pay", "bonus", "stock"))]


def test_approving_a_pay_rise_changes_no_prediction(client):
    employee_id = member(client)["id"]
    hr = login(client, "hr")
    before = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()
    nomination_id = recommend(client, employee_id).json()["id"]
    decide(client, nomination_id, approved_raise=15)
    after = client.post(f"/api/promotion/employees/{employee_id}/predict", headers=hr).json()
    assert before["score"] == after["score"] and before["contributions"] == after["contributions"]
