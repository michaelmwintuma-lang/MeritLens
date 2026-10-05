"""Finance signs off the pay rise of an approved promotion: nobody is told before that, Finance can send it back to
HR with a reason, HR resubmits, and every step is kept. Finance sees only what a pay decision needs."""
import pytest

from tests.conftest import emails_to, login, recommendation, sign_off

FINANCE_EMAIL, HR_EMAIL = "finance@example.org", "hr@example.org"
MANAGER_EMAIL, EMPLOYEE_EMAIL = "manager@example.org", "employee@example.org"


def approve(client, raise_percent=10, employee_id=None):
    """The manager recommends someone (by default the demo employee) and HR approves. Returns the decision."""
    if employee_id is None:
        employee_id = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    nomination = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(employee_id)).json()
    res = client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"),
                      json={"decision": "approve", "reason": "Strong evidence from the manager beyond the data.",
                            "approved_raise": raise_percent})
    assert res.status_code == 201, res.text
    return res.json()


def queue(client):
    return client.get("/api/finance/pay-reviews", headers=login(client, "finance")).json()


def send_back(client, decision_id, note="The department's pay budget for this quarter is already used."):
    return client.post(f"/api/finance/pay-reviews/{decision_id}/return", headers=login(client, "finance"), json={"note": note})


def count(address):
    return len(emails_to(address))


# ─── HR's approval waits for Finance ──────────────────────────────────────────
def test_an_approval_waits_for_finance_and_nobody_is_told_yet(client):
    manager_before, employee_before = count(MANAGER_EMAIL), count(EMPLOYEE_EMAIL)
    decision = approve(client)
    assert decision["pay_status"] == "awaiting_finance"
    assert [h["action"] for h in decision["pay_history"]] == ["submitted"]
    assert count(MANAGER_EMAIL) == manager_before and count(EMPLOYEE_EMAIL) == employee_before
    assert emails_to(FINANCE_EMAIL)[-1]["subject"].startswith("Pay rise to sign off: ")
    assert client.get("/api/promotion/my-promotions", headers=login(client, "employee")).json() == []


def test_a_rejection_never_goes_to_finance(client):
    employee_id = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    nomination = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(employee_id)).json()
    client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"), json={"decision": "reject"})
    assert queue(client)["reviews"] == []
    assert "Not approved" in emails_to(MANAGER_EMAIL)[-1]["text"]  # a rejection is told at once


# ─── What Finance sees ────────────────────────────────────────────────────────
def test_finance_sees_only_what_a_pay_decision_needs(client):
    approve(client, raise_percent=12)
    data = queue(client)
    row = data["reviews"][0]
    assert row["raise"] == 12 and row["within_policy"] and row["new_title"] and row["start"] and row["status"] == "awaiting_finance"
    assert data["policy"] == {"min_raise": 5.0, "max_raise": 15.0} and data["summary"]["awaiting"] == 1
    text = str(row).lower()
    for hidden in ("model", "score", "criteria", "rating", "strong evidence", "reason_for"):
        assert hidden not in text.replace("raise_reason", ""), hidden  # not the model's view, nor HR's or the manager's reasons


def test_a_rise_outside_the_policy_shows_hrs_reason(client):
    employee_id = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    nomination = client.post("/api/promotion/nominations", headers=login(client, "manager"), json=recommendation(employee_id)).json()
    client.post(f"/api/promotion/nominations/{nomination['id']}/decision", headers=login(client, "hr"),
                json={"decision": "approve", "reason": "Strong evidence from the manager beyond the data.", "approved_raise": 20,
                      "raise_reason": "Matching an outside offer to keep a key person."})
    row = queue(client)["reviews"][0]
    assert not row["within_policy"] and row["raise_reason"] == "Matching an outside offer to keep a key person."


# ─── Signing off ──────────────────────────────────────────────────────────────
def test_signing_off_makes_the_promotion_final(client):
    decision = approve(client, raise_percent=11)
    row = sign_off(client, decision["id"])
    assert row["status"] == "signed_off" and [h["action"] for h in row["history"]] == ["submitted", "signed_off"]
    assert row["history"][-1]["by"] == "Fay Finance"
    assert "11%" in emails_to(MANAGER_EMAIL)[-1]["text"] and "Finance has confirmed" in emails_to(MANAGER_EMAIL)[-1]["text"]
    assert emails_to(EMPLOYEE_EMAIL)[-1]["subject"] == "Your promotion has been approved"
    assert client.get("/api/promotion/my-promotions", headers=login(client, "employee")).json()[0]["raise"] == 11
    summary = queue(client)["summary"]
    assert summary["signed_off_this_year"] == 1 and summary["average_raise_this_year"] == 11
    assert summary["by_department"][0]["promotions"] == 1
    log = client.get("/api/admin/activity", headers=login(client, "admin")).json()["entries"]
    assert any(e["action"] == "pay_signed_off" for e in log)


def test_a_pay_rise_is_signed_off_only_once(client):
    decision = approve(client)
    sign_off(client, decision["id"])
    assert client.post(f"/api/finance/pay-reviews/{decision['id']}/sign-off", headers=login(client, "finance"), json={}).status_code == 409
    assert send_back(client, decision["id"]).status_code == 409


# ─── Sending back, and HR resubmitting ────────────────────────────────────────
def test_sending_back_needs_a_reason_and_tells_only_hr(client):
    decision = approve(client)
    manager_before = count(MANAGER_EMAIL)
    assert send_back(client, decision["id"], note="Too high.").status_code == 422
    res = send_back(client, decision["id"])
    assert res.status_code == 200 and res.json()["status"] == "returned"
    assert "pay budget" in emails_to(HR_EMAIL)[-1]["text"] and count(MANAGER_EMAIL) == manager_before
    assert client.post(f"/api/finance/pay-reviews/{decision['id']}/sign-off", headers=login(client, "finance"), json={}).status_code == 409


def test_hr_resubmits_a_revised_rise_and_finance_signs_it_off(client):
    decision = approve(client, raise_percent=14)
    hr = login(client, "hr")
    url = f"/api/promotion/decisions/{decision['id']}/resubmit"
    assert client.post(url, headers=hr, json={"approved_raise": 9, "note": "Lowered to fit the budget."}).status_code == 409  # not sent back yet
    send_back(client, decision["id"])
    assert client.post(url, headers=hr, json={"approved_raise": 25, "note": "Raised instead."}).status_code == 422  # outside policy, no reason
    res = client.post(url, headers=hr, json={"approved_raise": 9, "note": "Lowered to fit the budget."})
    assert res.status_code == 200 and res.json()["pay_status"] == "awaiting_finance" and res.json()["approved_raise"] == 9
    assert emails_to(FINANCE_EMAIL)[-1]["subject"].endswith("(revised)")
    row = sign_off(client, decision["id"])
    assert [(h["action"], h["raise"]) for h in row["history"]] == [("submitted", 14), ("returned", 14), ("resubmitted", 9), ("signed_off", 9)]
    assert "9%" in emails_to(EMPLOYEE_EMAIL)[-1]["text"]


# ─── Who can do what ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("username", ["employee", "manager", "hr", "admin"])
def test_only_finance_reviews_pay(client, username):
    decision = approve(client)
    headers = login(client, username)
    assert client.get("/api/finance/pay-reviews", headers=headers).status_code == 403
    assert client.post(f"/api/finance/pay-reviews/{decision['id']}/sign-off", headers=headers, json={}).status_code == 403


@pytest.mark.parametrize("username", ["employee", "manager", "finance", "admin"])
def test_only_hr_resubmits(client, username):
    decision = approve(client)
    send_back(client, decision["id"])
    res = client.post(f"/api/promotion/decisions/{decision['id']}/resubmit", headers=login(client, username),
                      json={"approved_raise": 9, "note": "Lowered to fit the budget."})
    assert res.status_code == 403


def test_finance_cant_change_the_pay_policy(client):
    assert client.put("/api/promotion/pay-policy", headers=login(client, "finance"), json={"min_raise": 1, "max_raise": 50}).status_code == 403
    assert client.get("/api/finance/pay-policy", headers=login(client, "finance")).json() == {"min_raise": 5.0, "max_raise": 15.0}


def test_hr_sees_the_pay_status_in_the_decision_log(client):
    decision = approve(client)
    send_back(client, decision["id"])
    entry = client.get("/api/promotion/decisions", headers=login(client, "hr")).json()[0]
    assert entry["pay_status"] == "returned" and entry["pay_history"][-1]["note"].startswith("The department's pay budget")


def test_finance_accounts_are_administration_accounts(client):
    admin = login(client, "admin")
    employee_id = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    linked = client.post("/api/admin/users", headers=admin, json={"username": "fin2", "full_name": "Second Finance",
                                                                  "email": "fin2@example.org", "role": "finance", "employee_id": employee_id})
    assert linked.status_code >= 400
    created = client.post("/api/admin/users", headers=admin, json={"username": "fin2", "full_name": "Second Finance",
                                                                   "email": "fin2@example.org", "role": "finance", "job_title": "Payroll Officer"})
    assert created.status_code == 201 and created.json()["user"]["role"] == "finance"


def test_the_manager_sees_the_approval_only_after_finance(client):
    decision = approve(client)
    mine = client.get("/api/promotion/nominations", headers=login(client, "manager")).json()[0]
    assert mine["status"] == "finalising" and mine["decision"] is None
    sign_off(client, decision["id"])
    mine = client.get("/api/promotion/nominations", headers=login(client, "manager")).json()[0]
    assert mine["status"] == "approved" and mine["decision"]["approved_raise"] == 10

