"""The employee feedback channel: rating explanations, record corrections, HR's queue, the committee note, re-appraisal."""
import json

import pytest

from tests.conftest import emails_to, login, recommendation

GOOD_NOTE = "My review form lists 9 projects; the record says fewer."


def me(client, username="employee"):
    return client.get("/api/auth/me", headers=login(client, username)).json()["employee_id"]


def rate(client, **body):
    return client.post("/api/feedback/ratings", headers=login(client, "employee"),
                       json={"clarity": 4, "usefulness": 5, "flagged": [], **body})


def ask(client, field="projects_completed", value=None, note=GOOD_NOTE):
    headers = login(client, "employee")
    if value is None:
        current = next(f for f in client.get("/api/feedback/fields", headers=headers).json() if f["name"] == field)["current"]
        value = current + 3
    return client.post("/api/feedback/corrections", headers=headers, json={"field": field, "requested_value": value, "note": note})


def score_of(client, employee_id):
    return client.post(f"/api/promotion/employees/{employee_id}/predict", headers=login(client, "hr")).json()["score"]


# ─── Rating the explanation ───────────────────────────────────────────────────
def test_an_employee_rates_their_explanation_with_the_model_version_and_score(client):
    res = rate(client, flagged=[{"feature": "late_days", "kind": "unfair"}], comment="Late days were a train strike.")
    assert res.status_code == 201
    from app.core.database import SessionLocal
    from app.feedback.models import ExplanationRating
    from app.promotion.explain import get_model
    with SessionLocal() as db:
        [rating] = db.query(ExplanationRating).all()
        assert rating.model_version == get_model().version
        assert rating.score == score_of(client, me(client))
        assert json.loads(rating.flagged_json) == [{"feature": "late_days", "kind": "unfair"}]


def test_rating_again_replaces_the_earlier_rating(client):
    rate(client, clarity=2)
    rate(client, clarity=5)
    mine = client.get("/api/feedback/ratings/mine", headers=login(client, "employee")).json()["rating"]
    assert mine["clarity"] == 5
    from app.core.database import SessionLocal
    from app.feedback.models import ExplanationRating
    with SessionLocal() as db:
        assert db.query(ExplanationRating).count() == 1


@pytest.mark.parametrize("body", [{"clarity": 6}, {"usefulness": 0},
                                  {"flagged": [{"feature": "gender", "kind": "unfair"}]},
                                  {"flagged": [{"feature": "late_days", "kind": "annoying"}]}])
def test_impossible_ratings_are_refused(client, body):
    assert rate(client, **body).status_code == 422


def test_a_rating_never_changes_a_score(client):
    employee_id = me(client)
    before = score_of(client, employee_id)
    rate(client, clarity=1, usefulness=1, flagged=[{"feature": f, "kind": "unfair"} for f in
                                                   ["performance_score", "late_days", "leadership_score"]])
    assert score_of(client, employee_id) == before


@pytest.mark.parametrize("username", ["manager", "hr", "admin", "finance", "auditor"])
def test_only_employees_rate_and_ask_for_corrections(client, username):
    headers = login(client, username)
    assert client.post("/api/feedback/ratings", headers=headers, json={"clarity": 4, "usefulness": 4}).status_code == 403
    assert client.post("/api/feedback/corrections", headers=headers,
                       json={"field": "late_days", "requested_value": 1, "note": GOOD_NOTE}).status_code == 403


def test_ratings_are_shown_only_in_aggregate_and_never_to_managers(client):
    rate(client, flagged=[{"feature": "late_days", "kind": "wrong"}])
    assert client.get("/api/feedback/ratings/summary", headers=login(client, "manager")).status_code == 403
    for username in ("hr", "auditor"):
        summary = client.get("/api/feedback/ratings/summary", headers=login(client, username)).json()
        assert summary["ratings"] == 1
        # Fewer than 5 ratings: no rates, so one person's answer can't be read off
        assert summary["clarity_rate"] is None and summary["usefulness_rate"] is None
        assert summary["contested"][0]["feature"] == "late_days" and summary["contested"][0]["share"] is None
        assert "comment" not in json.dumps(summary) and "employee" not in json.dumps(summary)


def test_with_enough_ratings_the_rates_are_shown(client):
    from app.core.database import SessionLocal
    from app.feedback.models import ExplanationRating
    with SessionLocal() as db:
        for i, clarity in enumerate([5, 4, 4, 2, 1]):
            db.add(ExplanationRating(employee_id=me(client), model_version=f"v{i}", score=0.1, clarity=clarity, usefulness=5))
        db.commit()
    summary = client.get("/api/feedback/ratings/summary", headers=login(client, "hr")).json()
    assert summary["clarity_rate"] == 0.6 and summary["usefulness_rate"] == 1.0


# ─── Asking for a correction ──────────────────────────────────────────────────
def test_only_values_from_the_record_can_be_corrected(client):
    fields = client.get("/api/feedback/fields", headers=login(client, "employee")).json()
    names = {f["name"] for f in fields}
    assert len(names) == 20 and "performance_last_year" in names and "performance_change" not in names
    assert not names & {"gender", "age", "education_level", "salary", "department"}
    assert ask(client, field="gender", value=1).status_code == 422


def test_a_request_needs_a_possible_value_a_change_and_evidence(client):
    assert ask(client, field="manager_rating", value=7).status_code == 422          # ratings are out of 5
    assert ask(client, field="projects_completed", value=6.5).status_code == 422    # whole numbers only
    assert ask(client, note="too short").status_code == 422                          # evidence in words
    current = next(f for f in client.get("/api/feedback/fields", headers=login(client, "employee")).json()
                   if f["name"] == "late_days")["current"]
    assert ask(client, field="late_days", value=current).status_code == 422          # nothing to change


def test_one_request_per_value_at_a_time(client):
    assert ask(client).status_code == 201
    assert ask(client).status_code == 409
    assert ask(client, field="late_days", value=0).status_code in (201, 422)  # another value is fine


def test_asking_changes_nothing_until_hr_confirms(client):
    employee_id = me(client)
    before = score_of(client, employee_id)
    ask(client)
    assert score_of(client, employee_id) == before
    assert emails_to("hr@example.org")[-1]["subject"].startswith("Record correction requested")


def test_managers_never_see_correction_requests(client):
    ask(client)
    manager = login(client, "manager")
    assert client.get("/api/hr/feedback/corrections", headers=manager).status_code == 403
    assert client.get("/api/feedback/corrections/mine", headers=manager).status_code == 403


def test_employees_cant_edit_the_data_the_model_uses(client):
    employee = login(client, "employee")
    employee_id = me(client)
    assert client.put(f"/api/promotion/records/{employee_id}", headers=employee, json={}).status_code == 403
    assert client.get(f"/api/promotion/records/{employee_id}", headers=employee).status_code == 403


# ─── Evidence files ───────────────────────────────────────────────────────────
def test_evidence_files_are_pdf_jpeg_or_png_and_only_hr_and_the_employee_see_them(client):
    request_id = ask(client).json()["id"]
    employee = login(client, "employee")
    upload = lambda data: client.post(f"/api/feedback/corrections/{request_id}/evidence", headers=employee,  # noqa: E731
                                      files={"file": ("x", data)})
    assert upload(b"just some text").status_code == 422
    assert upload(b"%PDF-1.4 a review form").status_code == 200
    assert client.get(f"/api/hr/feedback/corrections/{request_id}/evidence", headers=login(client, "hr")).content.startswith(b"%PDF")
    assert client.get(f"/api/feedback/corrections/{request_id}/evidence", headers=employee).status_code == 200
    assert client.get(f"/api/hr/feedback/corrections/{request_id}/evidence", headers=login(client, "manager")).status_code == 403


# ─── HR decides ───────────────────────────────────────────────────────────────
def test_hr_confirms_a_correction_the_employee_is_rescored_and_it_is_logged(client):
    employee_id = me(client)
    before = score_of(client, employee_id)
    request = ask(client).json()
    hr = login(client, "hr")
    verified = request["requested_value"]
    res = client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=hr,
                      json={"verified_value": verified, "note": "Checked against the signed review form."})
    assert res.status_code == 200 and res.json()["status"] == "confirmed"
    after = score_of(client, employee_id)
    assert after != before                                                   # the prediction changed

    [change] = client.get(f"/api/promotion/records/{employee_id}/history", headers=hr).json()
    assert change["source"] == "correction" and change["changed_by"] == "Hana Reviewer"
    assert change["changes"][0]["field"] == "projects_completed" and change["changes"][0]["new"] == verified
    assert change["score_before"] == before and change["score_after"] == after
    assert f"Correction request {request['id']}" in change["reason"]
    assert res.json()["score_before"] == before and res.json()["score_after"] == after
    assert emails_to("employee@example.org")[-1]["subject"] == "Your record correction: corrected"
    assert client.get("/api/feedback/notifications", headers=login(client, "employee")).json()[0]["status"] == "confirmed"


def test_hr_may_confirm_a_different_value_than_asked(client):
    request = ask(client).json()
    verified = request["current_value"] + 1
    client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=login(client, "hr"),
                json={"verified_value": verified})
    mine = client.get("/api/feedback/corrections/mine", headers=login(client, "employee")).json()[0]
    assert mine["verified_value"] == verified


def test_rejecting_needs_a_reason_the_employee_receives_and_changes_nothing(client):
    employee_id = me(client)
    before = score_of(client, employee_id)
    request = ask(client).json()
    hr = login(client, "hr")
    assert client.post(f"/api/hr/feedback/corrections/{request['id']}/reject", headers=hr, json={"reason": "No."}).status_code == 422
    reason = "The signed review form shows 6 projects, as recorded."
    assert client.post(f"/api/hr/feedback/corrections/{request['id']}/reject", headers=hr, json={"reason": reason}).status_code == 200
    assert score_of(client, employee_id) == before
    assert reason in emails_to("employee@example.org")[-1]["text"]
    assert client.get(f"/api/promotion/records/{employee_id}/history", headers=hr).json() == []
    # A decided request can't be decided again
    assert client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=hr,
                       json={"verified_value": request["requested_value"]}).status_code == 409


def test_seen_notifications_go_away(client):
    request = ask(client).json()
    client.post(f"/api/hr/feedback/corrections/{request['id']}/reject", headers=login(client, "hr"),
                json={"reason": "The record matches the signed review form."})
    employee = login(client, "employee")
    assert len(client.get("/api/feedback/notifications", headers=employee).json()) == 1
    client.post("/api/feedback/notifications/seen", headers=employee)
    assert client.get("/api/feedback/notifications", headers=employee).json() == []


# ─── The committee note and putting a decision on hold ────────────────────────
def nominate_the_employee(client):
    employee_id = me(client)
    res = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(employee_id))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_the_committee_sees_a_pending_correction_and_can_hold_the_decision(client):
    nomination_id = nominate_the_employee(client)
    hr = login(client, "hr")
    assert client.post(f"/api/hr/feedback/nominations/{nomination_id}/defer", headers=hr).status_code == 409  # nothing pending
    request = ask(client).json()
    note = client.get(f"/api/hr/feedback/nominations/{nomination_id}/note", headers=hr).json()
    assert [r["id"] for r in note["pending_corrections"]] == [request["id"]] and not note["deferred"]

    assert client.post(f"/api/hr/feedback/nominations/{nomination_id}/defer", headers=hr).json()["deferred"]
    # A hold is not a decision: nothing in the decision log, so it can't count as an override
    assert client.get("/api/promotion/decisions", headers=hr).json() == []
    # Resolving the correction takes the decision off hold
    client.post(f"/api/hr/feedback/corrections/{request['id']}/confirm", headers=hr,
                json={"verified_value": request["requested_value"]})
    note = client.get(f"/api/hr/feedback/nominations/{nomination_id}/note", headers=hr).json()
    assert note["pending_corrections"] == [] and not note["deferred"]


def test_hr_can_take_a_decision_off_hold(client):
    nomination_id = nominate_the_employee(client)
    ask(client)
    hr = login(client, "hr")
    client.post(f"/api/hr/feedback/nominations/{nomination_id}/defer", headers=hr)
    assert not client.post(f"/api/hr/feedback/nominations/{nomination_id}/resume", headers=hr).json()["deferred"]


def test_managers_dont_see_the_committee_note(client):
    nomination_id = nominate_the_employee(client)
    ask(client)
    assert client.get(f"/api/hr/feedback/nominations/{nomination_id}/note", headers=login(client, "manager")).status_code == 403
    described = client.get(f"/api/promotion/nominations/{nomination_id}", headers=login(client, "manager")).json()
    assert "correction" not in json.dumps(described).lower()
