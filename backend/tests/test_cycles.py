"""
Review cycles: everyone scored once and the scores kept; nominations and decisions belong to the cycle; a score in
an open cycle changes only through a logged record change; the nomination deadline; closing; fairness per cycle;
the model can't change mid-cycle; and who may see what.
"""
import csv
import io
from datetime import date, timedelta

from sqlalchemy import update

from app.core.database import SessionLocal
from app.governance import registry
from app.promotion.models import ReviewCycle
from tests.conftest import emails_to, login, recommendation
from tests.test_governance import make_candidate


def open_cycle(client, name="2026 mid-year", **extra):
    res = client.post("/api/promotion/cycles", headers=login(client, "hr"), json={"name": name, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def team(client):
    return client.get("/api/promotion/employees", headers=login(client, "manager")).json()


def nominate(client, person):
    res = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(person))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def decide(client, nomination, decision="reject"):
    body = {"decision": decision, "reason": "Not enough evidence of leadership in the new role yet."}
    if decision == "approve":
        body["approved_raise"] = 8
    res = client.post(f"/api/promotion/nominations/{nomination}/decision", headers=login(client, "hr"), json=body)
    assert res.status_code == 201, res.text


def test_opening_a_cycle_scores_everyone_once_and_saves_it(client):
    hr = login(client, "hr")
    live = client.get("/api/promotion/employees", headers=hr).json()
    assert live["cycle"] is None

    report = open_cycle(client, nominations_close=(date.today() + timedelta(days=14)).isoformat())
    assert report["cycle"]["status"] == "open" and report["cycle"]["model_version"] == live["model_version"]
    assert report["totals"]["people"] == len(live["employees"])
    assert report["totals"]["recommended"] == sum(e["recommended"] for e in live["employees"])
    assert report["cycle"]["days_left"] == 14 and report["cycle"]["nominations_open"]

    # The lists now show the saved scores, the same numbers the model gives
    saved = client.get("/api/promotion/employees", headers=hr).json()
    assert saved["cycle"]["id"] == report["cycle"]["id"]
    assert [e["score"] for e in saved["employees"]] == [e["score"] for e in live["employees"]]
    # Everyone signed in can see which cycle is open
    for username in ("employee", "manager", "finance", "auditor", "admin"):
        current = client.get("/api/promotion/cycles/current", headers=login(client, username)).json()["cycle"]
        assert current["name"] == "2026 mid-year"


def test_only_hr_opens_and_closes_and_only_one_cycle_is_open(client):
    for username in ("manager", "employee", "admin", "auditor", "finance"):
        assert client.post("/api/promotion/cycles", headers=login(client, username), json={"name": "Mine"}).status_code == 403
    cycle = open_cycle(client)["cycle"]
    again = client.post("/api/promotion/cycles", headers=login(client, "hr"), json={"name": "Another one"})
    assert again.status_code == 409 and "still open" in again.json()["detail"]
    assert client.post(f"/api/promotion/cycles/{cycle['id']}/close", headers=login(client, "auditor")).status_code == 403


def test_nominations_and_decisions_belong_to_the_open_cycle(client):
    cycle = open_cycle(client)["cycle"]
    person = team(client)["employees"][1]["id"]
    nomination = nominate(client, person)
    listed = client.get(f"/api/promotion/nominations/{nomination}", headers=login(client, "hr")).json()
    assert listed["cycle_id"] == cycle["id"]
    report = client.get(f"/api/promotion/cycles/{cycle['id']}", headers=login(client, "hr")).json()
    assert report["totals"]["nominated"] == 1 and report["totals"]["waiting"] == 1
    assert not report["can_close"] and "waiting for a decision" in report["close_blocker"]

    decide(client, nomination)
    report = client.get(f"/api/promotion/cycles/{cycle['id']}", headers=login(client, "hr")).json()
    assert report["totals"]["rejected"] == 1 and report["can_close"]


def test_no_nominations_after_the_deadline(client):
    cycle = open_cycle(client, nominations_close=date.today().isoformat())["cycle"]
    with SessionLocal() as db:  # the deadline was yesterday
        db.execute(update(ReviewCycle).where(ReviewCycle.id == cycle["id"])
                   .values(nominations_close=date.today() - timedelta(days=1)))
        db.commit()
    person = team(client)["employees"][1]["id"]
    res = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(person))
    assert res.status_code == 409 and "closed" in res.json()["detail"]


def test_a_deadline_must_be_in_the_coming_year(client):
    hr = login(client, "hr")
    for day in (date.today() - timedelta(days=1), date.today() + timedelta(days=400)):
        res = client.post("/api/promotion/cycles", headers=hr, json={"name": "Odd dates", "nominations_close": day.isoformat()})
        assert res.status_code == 422


def test_a_record_change_moves_the_saved_score_and_is_logged(client):
    hr = login(client, "hr")
    cycle = open_cycle(client)["cycle"]
    person = team(client)["employees"][0]["id"]
    before = next(e for e in client.get("/api/promotion/employees", headers=hr).json()["employees"] if e["id"] == person)

    record = client.get(f"/api/promotion/records/{person}", headers=hr).json()
    record["values"]["projects_completed"] += 6
    record["values"]["tasks_completed"] = round(record["values"]["tasks_completed"])  # the form takes whole numbers
    record["reason"] = "Six projects were missing from the review form."
    assert client.put(f"/api/promotion/records/{person}", headers=hr, json=record).status_code == 200

    after = next(e for e in client.get("/api/promotion/employees", headers=hr).json()["employees"] if e["id"] == person)
    live = client.post(f"/api/promotion/employees/{person}/predict", headers=hr).json()
    assert after["score"] == live["score"] != before["score"]
    [point] = client.get(f"/api/promotion/employees/{person}/trend", headers=hr).json()
    assert point["score_at_opening"] == before["score"] and point["score"] == after["score"] and point["rescored"]
    [change] = client.get(f"/api/promotion/records/{person}/history", headers=hr).json()
    assert change["score_after"] == after["score"]
    events = client.get("/api/governance/audit", headers=login(client, "auditor"), params={"event": "record_changed"}).json()
    assert events["events"][0]["payload"]["cycle_id"] == cycle["id"]


def test_someone_added_mid_cycle_is_scored_into_it(client):
    hr = login(client, "hr")
    cycle = open_cycle(client)["cycle"]
    record = client.get(f"/api/promotion/records/{team(client)['employees'][0]['id']}", headers=hr).json()
    record.update(full_name="New Starter", manager_user_id=None)
    record["values"]["tasks_completed"] = round(record["values"]["tasks_completed"])
    added = client.post("/api/promotion/records", headers=hr, json=record)
    assert added.status_code == 201, added.text
    listed = client.get("/api/promotion/employees", headers=hr).json()
    assert any(e["full_name"] == "New Starter" for e in listed["employees"])
    report = client.get(f"/api/promotion/cycles/{cycle['id']}", headers=hr).json()
    assert report["totals"]["added_late"] == 1


def test_closing_keeps_the_scores_and_the_next_cycle_shows_the_movement(client):
    hr = login(client, "hr")
    first = open_cycle(client, "2026 mid-year")["cycle"]
    closed = client.post(f"/api/promotion/cycles/{first['id']}/close", headers=hr)
    assert closed.status_code == 200 and closed.json()["cycle"]["status"] == "closed"
    assert client.post(f"/api/promotion/cycles/{first['id']}/close", headers=hr).status_code == 409
    assert client.get("/api/promotion/employees", headers=hr).json()["cycle"] is None  # back to scoring on demand

    second = open_cycle(client, "2026 year end")
    assert second["movement"]["previous"]["name"] == "2026 mid-year"
    assert second["movement"]["compared"] == second["totals"]["people"] and second["movement"]["average_change"] == 0
    person = team(client)["employees"][0]["id"]
    trend = client.get(f"/api/promotion/employees/{person}/trend", headers=login(client, "manager")).json()
    assert [p["name"] for p in trend] == ["2026 mid-year", "2026 year end"]
    names = [c["name"] for c in client.get("/api/promotion/cycles", headers=hr).json()]
    assert names == ["2026 year end", "2026 mid-year"]


def test_no_model_release_while_a_cycle_is_open(client):
    hr = login(client, "hr")
    new = make_candidate()
    cycle = open_cycle(client)["cycle"]
    note = {"note": "Retrained on this year's reviews; card checked by HR."}
    res = client.post(f"/api/governance/models/{new}/release", headers=hr, json=note)
    assert res.status_code == 409 and "review cycle" in res.json()["detail"]
    client.post(f"/api/promotion/cycles/{cycle['id']}/close", headers=hr)
    assert client.post(f"/api/governance/models/{new}/release", headers=hr, json=note).status_code == 200
    assert registry.live_version() == new


def test_the_auditor_sees_totals_but_never_a_named_person(client):
    cycle = open_cycle(client)["cycle"]
    hr_view = client.get(f"/api/promotion/cycles/{cycle['id']}", headers=login(client, "hr")).json()
    auditor_view = client.get(f"/api/promotion/cycles/{cycle['id']}", headers=login(client, "auditor")).json()
    assert "not_nominated" in hr_view and "not_nominated" not in auditor_view
    assert auditor_view["totals"] == hr_view["totals"]
    for username in ("manager", "employee", "finance", "admin"):
        assert client.get(f"/api/promotion/cycles/{cycle['id']}", headers=login(client, username)).status_code == 403
    assert client.get(f"/api/promotion/cycles/{cycle['id']}/export.csv", headers=login(client, "auditor")).status_code == 403


def test_hr_exports_a_cycle_as_csv(client):
    report = open_cycle(client)
    cycle = report["cycle"]
    person = team(client)["employees"][1]["id"]
    decide(client, nominate(client, person))
    res = client.get(f"/api/promotion/cycles/{cycle['id']}/export.csv", headers=login(client, "hr"))
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(res.text)))
    assert len(rows) == report["totals"]["people"]
    nominated = [r for r in rows if r["nominated"] == "yes"]
    assert len(nominated) == 1 and nominated[0]["decision"] == "reject" and int(nominated[0]["employee_id"]) == person


def test_trends_follow_who_may_see_a_score(client):
    open_cycle(client)
    own = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    assert len(client.get(f"/api/promotion/employees/{own}/trend", headers=login(client, "employee")).json()) == 1
    someone_else = next(e["id"] for e in client.get("/api/promotion/employees", headers=login(client, "hr")).json()["employees"]
                        if e["id"] != own)
    assert client.get(f"/api/promotion/employees/{someone_else}/trend", headers=login(client, "employee")).status_code == 403
    assert client.get(f"/api/promotion/employees/{own}/trend", headers=login(client, "auditor")).status_code == 403


def test_fairness_can_be_checked_for_one_cycle(client):
    cycle = open_cycle(client)["cycle"]
    report = client.get("/api/governance/fairness", headers=login(client, "auditor"), params={"cycle_id": cycle["id"]})
    assert report.status_code == 200
    assert report.json()["model_version"] == cycle["model_version"]
    assert client.get("/api/governance/fairness", headers=login(client, "hr"), params={"cycle_id": 999}).status_code == 404


def test_opening_and_closing_are_audited_and_managers_are_told(client):
    cycle = open_cycle(client, nominations_close=(date.today() + timedelta(days=10)).isoformat())["cycle"]
    client.post(f"/api/promotion/cycles/{cycle['id']}/close", headers=login(client, "hr"))
    events = client.get("/api/governance/audit", headers=login(client, "auditor")).json()["events"]
    kinds = [e["event"] for e in events]
    assert "cycle_opened" in kinds and "cycle_closed" in kinds
    assert client.get("/api/governance/audit/verify", headers=login(client, "auditor")).json()["intact"]
    manager = client.get("/api/auth/me", headers=login(client, "manager")).json()
    email = [e for e in emails_to(manager["email"]) if "Review cycle open" in e["subject"]][-1]  # the outbox is shared
    assert "2026 mid-year" in email["text"] and "Nominations close" in email["text"]
