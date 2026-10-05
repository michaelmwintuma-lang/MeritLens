"""Step 5 tests: nominations, HR decisions with the 20-character rule, the decision log, and managers' teams."""
from pathlib import Path

import pytest

from tests.conftest import login

pytestmark = pytest.mark.skipif(not (Path(__file__).resolve().parents[1] / "models" / "model.joblib").exists(),
                                reason="run train.py first")
REASON = "Led the migration project and mentored two new colleagues this year."


def team(client):
    return client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]


def everyone(client):
    return client.get("/api/promotion/employees", headers=login(client, "hr")).json()["employees"]


def manager_id(client):
    return client.get("/api/auth/me", headers=login(client, "manager")).json()["id"]


def nominate(client, employee_id, reason=REASON):
    return client.post("/api/promotion/nominations", headers=login(client, "manager"),
                       json={"employee_id": employee_id, "reason": reason})


def decide(client, nomination_id, decision, reason=None):
    return client.post(f"/api/promotion/nominations/{nomination_id}/decision", headers=login(client, "hr"),
                       json={"decision": decision, "reason": reason})


# ─── Nominating ───────────────────────────────────────────────────────────────
def test_manager_nominates_a_team_member(client):
    res = nominate(client, team(client)[0]["id"])
    assert res.status_code == 201 and res.json()["status"] == "pending"


def test_manager_cannot_nominate_outside_their_team(client):
    team_ids = {e["id"] for e in team(client)}
    outsider = next(e["id"] for e in everyone(client) if e["id"] not in team_ids)
    assert nominate(client, outsider).status_code == 403


@pytest.mark.parametrize("username", ["employee", "hr", "admin"])
def test_only_managers_nominate(client, username):
    employee_id = team(client)[0]["id"]
    res = client.post("/api/promotion/nominations", headers=login(client, username), json={"employee_id": employee_id, "reason": REASON})
    assert res.status_code == 403


def test_one_pending_nomination_per_person_and_a_real_reason(client):
    employee_id = team(client)[0]["id"]
    assert nominate(client, employee_id, reason="short").status_code == 422
    assert nominate(client, employee_id).status_code == 201
    assert nominate(client, employee_id).status_code == 409


def test_hr_sees_all_nominations_and_a_manager_only_their_own(client):
    nominate(client, team(client)[0]["id"])
    hr_view = client.get("/api/promotion/nominations", headers=login(client, "hr")).json()
    assert len(hr_view) == 1 and "model_now" in hr_view[0] and hr_view[0]["nominated_by"] == "Mo Manager"
    assert len(client.get("/api/promotion/nominations", headers=login(client, "manager")).json()) == 1
    assert client.get("/api/promotion/nominations", headers=login(client, "employee")).status_code == 403


# ─── Deciding ─────────────────────────────────────────────────────────────────
def not_recommended_nomination(client):
    """A nomination for a team member the model does NOT recommend (all the demo team are below the threshold)."""
    member = next(e for e in team(client) if not e["recommended"])
    return nominate(client, member["id"]).json()["id"]


def test_agreeing_with_the_model_needs_no_reason(client):
    res = decide(client, not_recommended_nomination(client), "reject")
    assert res.status_code == 201
    assert res.json()["agrees_with_model"] is True and res.json()["reason"] is None


def test_disagreeing_with_the_model_needs_a_20_character_reason(client):
    nomination_id = not_recommended_nomination(client)
    assert decide(client, nomination_id, "approve").status_code == 422
    assert decide(client, nomination_id, "approve", "Good work").status_code == 422          # under 20 characters
    res = decide(client, nomination_id, "approve", "Exceptional client feedback not in the data.")
    assert res.status_code == 201 and res.json()["agrees_with_model"] is False


def test_disagreeing_works_both_ways(client):
    """Rejecting someone the model recommends is also a disagreement."""
    recommended = next(e for e in everyone(client) if e["recommended"])
    admin = login(client, "admin")
    team_ids = [e["id"] for e in team(client)] + [recommended["id"]]
    assert client.put(f"/api/admin/users/{manager_id(client)}/team", headers=admin, json={"employee_ids": team_ids}).status_code == 200
    nomination_id = nominate(client, recommended["id"]).json()["id"]
    assert decide(client, nomination_id, "reject").status_code == 422
    assert decide(client, nomination_id, "reject", "Already promoted last quarter in a reorganisation.").status_code == 201


def test_only_hr_decides_and_only_once(client):
    nomination_id = not_recommended_nomination(client)
    for username in ["manager", "employee", "admin"]:
        res = client.post(f"/api/promotion/nominations/{nomination_id}/decision", headers=login(client, username), json={"decision": "reject"})
        assert res.status_code == 403
    assert decide(client, nomination_id, "reject").status_code == 201
    assert decide(client, nomination_id, "reject").status_code == 409


# ─── Decision log ─────────────────────────────────────────────────────────────
def test_every_decision_is_logged_with_the_models_view(client):
    nomination_id = not_recommended_nomination(client)
    decide(client, nomination_id, "approve", "Exceptional client feedback not in the data.")
    log = client.get("/api/promotion/decisions", headers=login(client, "hr")).json()
    assert len(log) == 1
    entry = log[0]
    assert entry["decided_by"] == "Hana Reviewer" and entry["decision"] == "approve" and entry["decided_at"]
    assert entry["model_recommended"] is False and 0 <= entry["model_score"] < entry["model_threshold"]
    assert entry["reason"] == "Exceptional client feedback not in the data."
    nomination = client.get(f"/api/promotion/nominations/{nomination_id}", headers=login(client, "manager")).json()
    assert nomination["status"] == "approved" and nomination["decision"]["id"] == entry["id"]


@pytest.mark.parametrize("username", ["manager", "employee", "admin"])
def test_only_hr_reads_the_decision_log(client, username):
    assert client.get("/api/promotion/decisions", headers=login(client, username)).status_code == 403


# ─── Managers' teams (set by the admin) ───────────────────────────────────────
def test_admin_sets_a_managers_team(client):
    admin = login(client, "admin")
    directory = client.get("/api/admin/employees", headers=admin).json()
    assert len(directory) == 120 and "score" not in directory[0]  # admins see names, not scores
    new_team = [e["id"] for e in directory[:3]]
    res = client.put(f"/api/admin/users/{manager_id(client)}/team", headers=admin, json={"employee_ids": new_team})
    assert res.status_code == 200
    assert sorted(e["id"] for e in team(client)) == sorted(new_team)


def test_teams_only_for_managers_and_only_by_the_admin(client):
    admin = login(client, "admin")
    hr_id = client.get("/api/auth/me", headers=login(client, "hr")).json()["id"]
    assert client.put(f"/api/admin/users/{hr_id}/team", headers=admin, json={"employee_ids": []}).status_code == 400
    assert client.put(f"/api/admin/users/{manager_id(client)}/team", headers=admin, json={"employee_ids": [999999999]}).status_code == 404
    assert client.put(f"/api/admin/users/{manager_id(client)}/team", headers=login(client, "hr"), json={"employee_ids": []}).status_code == 403
