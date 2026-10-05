"""Step 7 tests: triage, the conversation between reporter and investigator, and HR's inbox and case updates."""
import pytest

from app.reporting.triage import triage
from tests.conftest import login

TEXT = "My manager shouted at me and humiliated me in front of the whole team again this week."


def submit(client, text=TEXT, category="bullying"):
    return client.post("/api/reports", headers=login(client, "employee"), json={"category": category, "text": text}).json()


def reporter(client, case, path="/api/reports/access", **extra):
    return client.post(path, headers=login(client, "employee"), json={"case_id": case["case_id"], "key": case["key"], **extra})


def hr(client):
    return login(client, "hr")


# ─── Triage ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text, category, expected", [
    ("He threatened me in the car park and I feel unsafe.", "other", "high"),
    ("He hit me on the arm during the meeting.", "other", "high"),
    ("My manager shouted at me and humiliated me.", "other", "medium"),
    ("I would like more flexible hours for everyone.", "other", "low"),
])
def test_triage_sets_the_priority(text, category, expected):
    assert triage(text, category)["priority"] == expected


def test_harmless_phrases_are_ignored():
    result = triage("We hit our targets, the deadline is killing me and we killed it in the demo.", "other")
    assert result["priority"] == "low" and result["triggers"] == []


def test_category_minimums():
    assert triage("The fire exit is often locked.", "safety")["priority"] == "high"
    assert triage("I was given less training than colleagues.", "harassment")["priority"] == "medium"
    assert triage("I was given less training than colleagues.", "discrimination")["priority"] == "medium"


def test_the_words_behind_the_priority_are_returned():
    result = triage("He threatened me and shouted.", "other")
    assert {"word": "threatened", "level": "high"} in result["triggers"] and result["reasons"]


def test_a_new_report_gets_the_suggested_priority(client):
    case = submit(client)
    detail = client.get(f"/api/hr/reports/{case['case_id']}", headers=hr(client)).json()
    assert detail["priority"] == detail["suggested_priority"] == "medium"
    # The words marked in the text are the ones that drove the language model, and its reading is shown
    reading = detail["triage"]["model"]
    assert reading["priority"] == "medium" and {t["word"] for t in detail["triage"]["triggers"]} == {w["word"] for w in reading["words"]}
    assert detail["triage"]["reasons"][0].startswith("The language model read this as moderate priority")


# ─── Conversation ─────────────────────────────────────────────────────────────
def test_investigator_and_reporter_talk_without_names(client):
    case = submit(client)
    assert client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=hr(client),
                       json={"text": "Thank you for reporting. Can you say how often this happens?"}).status_code == 201
    assert reporter(client, case, "/api/reports/messages", text="Almost every week, usually on Mondays.").status_code == 201
    seen_by_reporter = reporter(client, case).json()["messages"]
    seen_by_hr = client.get(f"/api/hr/reports/{case['case_id']}", headers=hr(client)).json()["conversation"]
    assert [m["sender"] for m in seen_by_reporter] == [m["sender"] for m in seen_by_hr] == ["investigator", "reporter"]
    everything = str(seen_by_reporter) + str(seen_by_hr)
    for name in ["Hana Reviewer", "Eli Employee", "hr", "employee"]:
        assert f"'{name}'" not in everything  # no names or usernames anywhere in the conversation


def test_reporter_messages_must_be_anonymised(client):
    case = submit(client)
    res = reporter(client, case, "/api/reports/messages", text="It was Hana Reviewer who saw it, call me on 07700 900123.")
    assert res.status_code == 422


def test_replying_needs_the_key(client):
    case = submit(client)
    res = client.post("/api/reports/messages", headers=login(client, "employee"),
                      json={"case_id": case["case_id"], "key": "AAAA-AAAA-AAAA-AAAA", "text": "Hello there"})
    assert res.status_code == 403


def test_reporter_does_not_see_priority(client):
    case = submit(client)
    view = reporter(client, case).json()
    assert "priority" not in view and "suggested_priority" not in view


def test_first_reply_marks_the_case_investigating(client):
    case = submit(client)
    res = client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=hr(client), json={"text": "We are looking into it."})
    assert res.json()["status"] == "investigating"


# ─── HR updates and the inbox ─────────────────────────────────────────────────
def test_hr_changes_priority_and_closing_needs_an_outcome(client):
    case_id = submit(client)["case_id"]
    url = f"/api/hr/reports/{case_id}"
    assert client.patch(url, headers=hr(client), json={"priority": "high"}).json()["priority"] == "high"
    assert client.patch(url, headers=hr(client), json={"status": "closed"}).status_code == 422
    closed = client.patch(url, headers=hr(client), json={"status": "closed", "outcome": "substantiated"}).json()
    assert closed["status"] == "closed" and closed["outcome"] == "substantiated"
    assert client.patch(url, headers=hr(client), json={"priority": "urgent"}).status_code == 422


def test_reporter_sees_the_outcome_and_cannot_write_to_a_closed_case(client):
    case = submit(client)
    client.patch(f"/api/hr/reports/{case['case_id']}", headers=hr(client), json={"status": "closed", "outcome": "resolved"})
    view = reporter(client, case).json()
    assert view["status"] == "closed" and view["outcome"] == "Resolved informally"
    assert reporter(client, case, "/api/reports/messages", text="One more thing").status_code == 409


def test_inbox_shows_open_high_priority_first_and_who_wrote_last(client):
    low = submit(client, "I would like more flexible hours for everyone in our area.", "other")
    high = submit(client, "He threatened me in the car park last week and I feel unsafe.", "other")
    reporter(client, low, "/api/reports/messages", text="Any news on this please?")
    inbox = client.get("/api/hr/reports", headers=hr(client)).json()
    assert [r["case_id"] for r in inbox][:2] == [high["case_id"], low["case_id"]]
    assert next(r for r in inbox if r["case_id"] == low["case_id"])["reporter_wrote_last"] is True


@pytest.mark.parametrize("username", ["employee", "manager", "admin"])
def test_only_hr_sees_the_inbox(client, username):
    case_id = submit(client)["case_id"]
    headers = login(client, username)
    assert client.get("/api/hr/reports", headers=headers).status_code == 403
    assert client.get(f"/api/hr/reports/{case_id}", headers=headers).status_code == 403
    assert client.post(f"/api/hr/reports/{case_id}/messages", headers=headers, json={"text": "hello"}).status_code == 403
