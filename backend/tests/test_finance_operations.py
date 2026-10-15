"""
Finance at work: how long each pay rise has waited, signing off several at once (only within the pay policy), review
cycles in Finance, how signed-off rises spread, and the hand-over to payroll (once each).
"""
import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import update

from app.core.database import SessionLocal
from app.promotion.models import PayReview
from tests.conftest import emails_to, login, recommendation


def approve(client, index, raise_percent=8, **extra):
    """The manager recommends team member `index`; HR approves with this pay rise. Returns the decision id."""
    team = client.get("/api/promotion/employees", headers=login(client, "manager")).json()["employees"]
    nomination = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(team[index]["id"]))
    assert nomination.status_code == 201, nomination.text
    body = {"decision": "approve", "reason": "Strong case for the promotion from the manager.", "approved_raise": raise_percent, **extra}
    decision = client.post(f"/api/promotion/nominations/{nomination.json()['id']}/decision", headers=login(client, "hr"), json=body)
    assert decision.status_code == 201, decision.text
    return decision.json()["id"]


def reviews(client, **params):
    return client.get("/api/finance/pay-reviews", headers=login(client, "finance"), params=params).json()


def test_each_waiting_pay_rise_says_how_long_it_has_waited_longest_first(client):
    first, second = approve(client, 1), approve(client, 2)
    with SessionLocal() as db:  # the first reached Finance a week ago
        db.execute(update(PayReview).where(PayReview.decision_id == first).values(at=datetime.now() - timedelta(days=7)))
        db.commit()
    rows = reviews(client)["reviews"]
    assert [r["id"] for r in rows[:2]] == [first, second]
    assert rows[0]["waiting_days"] >= 4 and rows[1]["waiting_days"] == 0
    assert reviews(client)["summary"]["waiting_longest"] == rows[0]["waiting_days"]


def test_several_within_policy_rises_are_signed_off_at_once_each_on_its_own_record(client):
    first, second = approve(client, 1), approve(client, 2)
    res = client.post("/api/finance/pay-reviews/sign-off-many", headers=login(client, "finance"), json={"ids": [first, second]})
    assert res.status_code == 200 and res.json()["signed_off"] == 2
    rows = {r["id"]: r for r in reviews(client)["reviews"]}
    assert rows[first]["status"] == rows[second]["status"] == "signed_off"
    assert [h["action"] for h in rows[first]["history"]] == ["submitted", "signed_off"]
    events = client.get("/api/governance/audit", headers=login(client, "auditor"), params={"event": "pay_signed_off"}).json()
    assert events["total"] == 2
    assert len([e for e in emails_to("manager@example.org") if e["subject"].startswith("Decision on your nomination")]) == 2


def test_a_rise_outside_the_policy_is_never_signed_off_in_bulk(client):
    inside = approve(client, 1)
    outside = approve(client, 2, raise_percent=20, raise_reason="Exceptional market pressure for this role this year.")
    res = client.post("/api/finance/pay-reviews/sign-off-many", headers=login(client, "finance"), json={"ids": [inside, outside]})
    assert res.status_code == 409 and "Outside the pay policy" in res.json()["detail"]
    assert all(r["status"] == "awaiting_finance" for r in reviews(client)["reviews"])  # nothing signed off
    assert client.post("/api/finance/pay-reviews/sign-off-many", headers=login(client, "hr"), json={"ids": [inside]}).status_code == 403


def test_finance_filters_by_review_cycle(client):
    before = approve(client, 1)
    cycle = client.post("/api/promotion/cycles", headers=login(client, "hr"), json={"name": "2026 year end"}).json()["cycle"]
    during = approve(client, 2)
    data = reviews(client)
    assert data["cycles"] == [{"id": cycle["id"], "name": "2026 year end"}]
    rows = {r["id"]: r for r in data["reviews"]}
    assert rows[during]["cycle"]["name"] == "2026 year end" and rows[before]["cycle"] is None
    assert [r["id"] for r in reviews(client, cycle_id=cycle["id"])["reviews"]] == [during]


def test_signed_off_rises_go_to_payroll_once(client):
    first, second = approve(client, 1, raise_percent=8), approve(client, 2, raise_percent=10)
    finance = login(client, "finance")
    client.post("/api/finance/pay-reviews/sign-off-many", headers=finance, json={"ids": [first, second]})
    summary = reviews(client)["summary"]
    assert summary["payroll_waiting"] == 2
    assert summary["distribution"] == [{"raise": 8.0, "count": 1, "within_policy": True}, {"raise": 10.0, "count": 1, "within_policy": True}]

    sheet = list(csv.DictReader(io.StringIO(client.get("/api/finance/payroll.csv", headers=finance).text)))
    assert {int(r["decision_id"]) for r in sheet} == {first, second}
    assert all(r["pay_rise_percent"] and r["signed_off_on"] and not r["sent_to_payroll_on"] for r in sheet)

    marked = client.post("/api/finance/payroll/mark-sent", headers=finance, json={"ids": [first]}).json()
    assert marked == {"marked": 1, "already": 0}
    assert client.post("/api/finance/payroll/mark-sent", headers=finance, json={"ids": [first]}).json() == {"marked": 0, "already": 1}
    still = list(csv.DictReader(io.StringIO(client.get("/api/finance/payroll.csv", headers=finance).text)))
    assert [int(r["decision_id"]) for r in still] == [second]
    everything = list(csv.DictReader(io.StringIO(client.get("/api/finance/payroll.csv", headers=finance, params={"include_sent": True}).text)))
    assert len(everything) == 2
    assert reviews(client)["summary"]["payroll_waiting"] == 1
    events = client.get("/api/governance/audit", headers=login(client, "auditor"), params={"event": "payroll_sent"}).json()
    assert events["total"] == 1


def test_only_signed_off_rises_go_to_payroll_and_only_finance_sends_them(client):
    waiting = approve(client, 1)
    finance = login(client, "finance")
    assert client.post("/api/finance/payroll/mark-sent", headers=finance, json={"ids": [waiting]}).status_code == 409
    for username in ("hr", "admin", "auditor"):
        assert client.get("/api/finance/payroll.csv", headers=login(client, username)).status_code == 403
