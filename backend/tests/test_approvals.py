"""
The four-eyes rule (FOUR_EYES=1): a model release, and a record correction that moves someone across the threshold,
wait for a second HR person; the person who asked can't approve their own request. Off, nothing changes.
"""
import json

import pytest

from app.core import config
from app.core.database import SessionLocal
from app.governance import registry
from app.promotion.models import Employee
from app.promotion.routes import model
from tests.conftest import login
from tests.test_feedback import ask
from tests.test_governance import make_candidate

NOTE = {"note": "Retrained on this year's reviews; card checked by HR."}


@pytest.fixture
def four_eyes(client, monkeypatch):
    """The rule on, and a second HR account ("hr2") to approve."""
    monkeypatch.setattr(config, "FOUR_EYES", True)
    made = client.post("/api/admin/users", headers=login(client, "admin"),
                       json={"username": "hr2", "full_name": "Second HR", "email": "hr2@example.org", "role": "hr"}).json()
    hr2 = login(client, "hr2", made["temporary_password"])
    return login(client, "hr"), hr2


def test_with_the_rule_off_a_release_happens_at_once(client):
    new = make_candidate()
    assert client.post(f"/api/governance/models/{new}/release", headers=login(client, "hr"), json=NOTE).status_code == 200
    assert client.get("/api/approvals", headers=login(client, "hr")).json() == {"four_eyes": False, "items": []}


def test_a_release_waits_for_a_second_hr_person(client, four_eyes):
    hr, hr2 = four_eyes
    old, new = registry.live_version(), make_candidate()
    asked = client.post(f"/api/governance/models/{new}/release", headers=hr, json=NOTE)
    assert asked.status_code == 202 and registry.live_version() == old  # nothing changed yet
    approval = asked.json()["approval"]
    assert approval["kind"] == "model_release" and approval["status"] == "pending"
    # Asking twice, or approving your own request, is refused
    assert client.post(f"/api/governance/models/{new}/release", headers=hr, json=NOTE).status_code == 409
    assert client.post(f"/api/approvals/{approval['id']}/approve", headers=hr, json={}).status_code == 403
    assert client.post(f"/api/approvals/{approval['id']}/approve", headers=login(client, "admin"), json={}).status_code == 403

    done = client.post(f"/api/approvals/{approval['id']}/approve", headers=hr2, json={"note": "Card read."})
    assert done.status_code == 200 and done.json()["approval"]["decided_by"] == "Second HR"
    assert registry.live_version() == new
    [release] = registry.release_history(SessionLocal(), new)
    assert "approved by Second HR" in release["note"] and release["released_by"] != "Second HR"
    assert client.post(f"/api/approvals/{approval['id']}/approve", headers=hr2, json={}).status_code == 409


def test_a_declined_release_changes_nothing_and_needs_a_reason(client, four_eyes):
    hr, hr2 = four_eyes
    old, new = registry.live_version(), make_candidate()
    approval = client.post(f"/api/governance/models/{new}/release", headers=hr, json=NOTE).json()["approval"]
    assert client.post(f"/api/approvals/{approval['id']}/decline", headers=hr2, json={}).status_code == 422
    res = client.post(f"/api/approvals/{approval['id']}/decline", headers=hr2, json={"note": "Wait for the next quarter."})
    assert res.status_code == 200 and res.json()["approval"]["status"] == "declined"
    assert registry.live_version() == old
    assert client.get("/api/approvals", headers=hr).json()["items"] == []


def crossing_correction(client, monkeypatch):
    """A correction request whose confirmation moves the employee across the threshold (set between the two scores)."""
    request = ask(client).json()
    with SessionLocal() as db:
        employee = db.get(Employee, request["employee_id"])
        old = json.loads(employee.record_json)
    new = {**old, request["field"]: request["requested_value"]}
    live = model()
    before, after = live.score(old), live.score(new)
    assert before != after
    monkeypatch.setattr(live, "threshold", (before + after) / 2)
    return request


def test_a_correction_that_crosses_the_threshold_waits_for_a_second_hr_person(client, four_eyes, monkeypatch):
    hr, hr2 = four_eyes
    request = crossing_correction(client, monkeypatch)
    value = {"verified_value": request["requested_value"], "note": "Checked the project list."}
    asked = client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=hr, json=value)
    assert asked.status_code == 202 and "threshold" in asked.json()["approval"]["summary"]
    queue = {r["id"]: r["status"] for r in client.get("/api/hr/feedback/corrections", headers=hr).json()}
    assert queue[request["id"]] == "pending"

    approval = asked.json()["approval"]
    done = client.post(f"/api/approvals/{approval['id']}/approve", headers=hr2, json={})
    assert done.status_code == 200 and done.json()["result"]["status"] == "confirmed"
    assert "approved by Second HR" in done.json()["result"]["decision_reason"]


def test_rejecting_the_correction_closes_its_waiting_approval(client, four_eyes, monkeypatch):
    hr, hr2 = four_eyes
    request = crossing_correction(client, monkeypatch)
    client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=hr,
                json={"verified_value": request["requested_value"]})
    res = client.post(f"/api/hr/feedback/corrections/{request['id']}/reject", headers=hr2,
                      json={"reason": "The evidence shows the projects were in another year."})
    assert res.status_code == 200
    assert client.get("/api/approvals", headers=hr).json()["items"] == []
