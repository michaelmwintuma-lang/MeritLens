"""Step 6 tests: the anonymiser, submitting a report, keys, the lockout, what is (not) stored, and isolation."""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.reporting.anonymiser import anonymise
from app.reporting.models import Report
from app.reporting.routes import MAX_ATTEMPTS, SAME_ERROR
from tests.conftest import login

NAMES = ["Amara Castillo", "Ben Quinn", "Hannah Castillo"]
TEXT = "My manager keeps shouting at me in meetings and it has gone on for weeks now."


# ─── Anonymiser ───────────────────────────────────────────────────────────────
def test_directory_names_are_replaced_and_the_same_person_keeps_one_tag():
    result = anonymise("Ben Quinn shouted. Later Ben did it again while Amara Castillo watched.", NAMES)
    assert "Ben" not in result["text"] and "Amara" not in result["text"]
    assert result["text"].count("[PERSON 1]") + result["text"].count("[PERSON 2]") == 3
    tags = {r["original"]: r["tag"] for r in result["replaced"]}
    assert tags["Ben Quinn"] == tags["Ben"]


def test_emails_phones_and_dates_are_replaced():
    text = "Write to ben.q@company.com or call +44 7700 900123. It was on 12 March 2025 and again on 03/04/2025."
    cleaned = anonymise(text, NAMES)["text"]
    for leftover in ["ben.q@", "7700", "March", "03/04"]:
        assert leftover not in cleaned
    assert "[EMAIL 1]" in cleaned and "[PHONE 1]" in cleaned and "[DATE 2]" in cleaned


def test_ordinary_text_is_left_alone():
    text = "We hit our targets this quarter and the team of 12 people did well."
    assert anonymise(text, NAMES)["text"] == text


def test_identifying_phrases_are_flagged_once():
    result = anonymise("I'm the only woman in the team. I have worked here for 12 years.", NAMES)
    reasons = [w["reason"] for w in result["warnings"]]
    assert len(reasons) == 2


# ─── Submitting ───────────────────────────────────────────────────────────────
def submit(client, user="employee", text=TEXT, category="harassment"):
    return client.post("/api/reports", headers=login(client, user), json={"category": category, "text": text})


def test_only_signed_in_members_can_report(client):
    assert client.post("/api/reports", json={"category": "harassment", "text": TEXT}).status_code == 401
    assert client.post("/api/reports/preview", json={"text": TEXT}).status_code == 401


def test_preview_stores_nothing(client):
    res = client.post("/api/reports/preview", headers=login(client, "employee"),
                      json={"text": "Mo Manager shouted at me on 3 May and I'm the only woman here."})
    assert res.status_code == 200 and "[PERSON 1]" in res.json()["text"] and res.json()["warnings"]
    with SessionLocal() as db:
        assert db.query(Report).count() == 0


def test_a_report_gives_a_case_id_and_key_and_stores_only_a_hash(client):
    res = submit(client)
    assert res.status_code == 201
    body = res.json()
    assert re.fullmatch(r"R-[A-Z2-9]{4}-[A-Z2-9]{4}", body["case_id"])
    assert re.fullmatch(r"([A-Z2-9]{4}-){3}[A-Z2-9]{4}", body["key"])
    with SessionLocal() as db:
        report = db.get(Report, body["case_id"])
        assert body["key"] not in report.key_hash and report.key_hash.startswith("pbkdf2_sha256$")
        assert isinstance(report.created_on, date) and not isinstance(report.created_on, datetime)  # the day, no time


def test_nothing_about_the_reporter_is_stored(client):
    """The reports table has no column that could hold the reporter's identity or exact time."""
    columns = {c["name"] for c in inspect(engine).get_columns("reports")}
    assert columns == {"case_id", "category", "text", "created_on", "key_hash", "suggested_priority", "priority",
                       "status", "outcome", "failed_attempts", "locked_until"}
    # Messages: sender is only "reporter" or "investigator", and only the date is kept
    assert {c["name"] for c in inspect(engine).get_columns("report_messages")} == {"case_id", "number", "sender", "text", "sent_on"}
    me = client.get("/api/auth/me", headers=login(client, "employee")).json()
    body = submit(client).json()
    with SessionLocal() as db:
        stored = " ".join(str(v) for v in vars(db.get(Report, body["case_id"])).values())
    for identifying in [me["username"], me["full_name"], str(me["id"]) + ",", str(me["employee_id"])]:
        assert identifying not in stored


def test_reports_have_no_hidden_order(client):
    """No rowid: the storage order can't be matched against sign-in times."""
    with engine.connect() as conn:
        sql = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name = 'reports'").scalar()
    assert "WITHOUT ROWID" in sql.upper()


def test_text_that_still_identifies_someone_is_refused(client):
    assert submit(client, text="Hana Reviewer keeps shouting at me in every single meeting.").status_code == 422
    assert submit(client, text="Please call me on 07700 900123 about the shouting in meetings.").status_code == 422
    assert submit(client, category="gossip").status_code == 422


@pytest.mark.parametrize("user", ["employee", "manager"])
def test_employees_and_managers_can_report(client, user):
    assert submit(client, user=user).status_code == 201


@pytest.mark.parametrize("user", ["hr", "admin"])
def test_hr_and_admins_do_not_use_the_reporting_pages(client, user):
    """HR handles reports in the inbox; admins manage accounts. Neither reports through the system."""
    headers = login(client, user)
    assert submit(client, user=user).status_code == 403
    assert client.post("/api/reports/preview", headers=headers, json={"text": TEXT}).status_code == 403
    assert client.post("/api/reports/access", headers=headers, json={"case_id": "R-AAAA-AAAA", "key": "x"}).status_code == 403


# ─── Opening a case with the key ──────────────────────────────────────────────
def access(client, case_id, key):
    return client.post("/api/reports/access", headers=login(client, "employee"), json={"case_id": case_id, "key": key})


def test_the_key_opens_the_case(client):
    body = submit(client).json()
    res = access(client, body["case_id"], body["key"])
    assert res.status_code == 200 and res.json()["text"] == TEXT and res.json()["status"] == "open"


def test_wrong_case_and_wrong_key_get_the_same_answer(client):
    body = submit(client).json()
    wrong_key = access(client, body["case_id"], "AAAA-AAAA-AAAA-AAAA")
    wrong_case = access(client, "R-AAAA-AAAA", body["key"])
    assert wrong_key.status_code == wrong_case.status_code == 403
    assert wrong_key.json() == wrong_case.json() == {"detail": SAME_ERROR}


def test_five_wrong_keys_lock_the_case_for_15_minutes(client):
    body = submit(client).json()
    for _ in range(MAX_ATTEMPTS):
        access(client, body["case_id"], "AAAA-AAAA-AAAA-AAAA")
    locked = access(client, body["case_id"], body["key"])  # even the right key is refused while locked
    assert locked.status_code == 403 and locked.json()["detail"] == SAME_ERROR
    with SessionLocal() as db:  # pretend 15 minutes have passed
        report = db.get(Report, body["case_id"])
        report.locked_until = datetime.now() - timedelta(seconds=1)
        db.commit()
    assert access(client, body["case_id"], body["key"]).status_code == 200


# ─── Isolation: report data never reaches the promotion model ─────────────────
def test_promotion_code_never_imports_the_reporting_code():
    promotion = Path(__file__).resolve().parents[1] / "app" / "promotion"
    for file in [*promotion.glob("*.py"), Path(__file__).resolve().parents[1] / "train.py"]:
        source = file.read_text(encoding="utf-8")
        assert "reporting" not in source and "Report" not in source.replace("Reporter", ""), file.name


def test_predictions_are_identical_before_and_after_reports(client):
    hr = login(client, "hr")
    before = client.get("/api/promotion/employees", headers=hr).json()
    for category in ["harassment", "discrimination", "bullying"]:
        submit(client, category=category)
    after = client.get("/api/promotion/employees", headers=hr).json()
    assert before == after


def test_surnames_that_are_ordinary_words_are_only_replaced_when_capitalised():
    names = ["Tara Brooks"]
    assert anonymise("Water brooks run past the office and my manager complains.", names + ["Mo Manager"])["text"] == \
        "Water brooks run past the office and my manager complains."
    assert "Brooks" not in anonymise("Brooks was rude to me again.", names)["text"]
