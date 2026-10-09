"""
Isolation: feedback and reports never change a prediction. Only HR confirming a record correction does, and that
is logged.

1. End to end: an employee's prediction and explanation are recorded; then ratings, anonymous reports, case
   conversations, case outcomes and correction requests about that employee and their manager are added; the
   prediction and explanation must be byte-for-byte identical. Then HR confirms a correction: the prediction
   must change, and the change must be logged.
2. Static: no file in the promotion code imports, or even names, the feedback or reporting code and tables.
3. At run time: the prediction endpoints run no SQL that touches a feedback or reporting table.
"""
import ast
from pathlib import Path

import pytest
from sqlalchemy import event

from app.core.database import Base, engine
from tests.conftest import login, recommendation

PROMOTION = Path(__file__).resolve().parents[1] / "app" / "promotion"
FEEDBACK_AND_REPORT_TABLES = {"explanation_ratings", "correction_requests", "nomination_deferrals",
                              "reports", "report_messages", "report_evidence"}


def employee_id(client):
    return client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]


def prediction_bytes(client, person: int) -> dict:
    """Every prediction endpoint's exact answer for one employee, as HR, their manager and they see it."""
    hr, manager, employee = login(client, "hr"), login(client, "manager"), login(client, "employee")
    return {
        "explanation (HR)": client.get(f"/api/promotion/employees/{person}", headers=hr).content,
        "explanation (manager)": client.get(f"/api/promotion/employees/{person}", headers=manager).content,
        "explanation (employee)": client.get(f"/api/promotion/employees/{person}", headers=employee).content,
        "tips": client.get(f"/api/promotion/employees/{person}/tips", headers=hr).content,
        "what-if": client.post(f"/api/promotion/employees/{person}/what-if", headers=hr,
                               json={"changes": {"training_hours_last_year": 60}}).content,
        "everyone's scores": client.get("/api/promotion/employees", headers=hr).content,
        "team's scores": client.get("/api/promotion/employees", headers=manager).content,
        "importance": client.get("/api/promotion/importance", headers=hr).content,
    }


def add_every_kind_of_feedback_and_report(client, person: int) -> None:
    """Ratings, reports, conversations and outcomes about the employee and their manager, and correction requests."""
    employee, hr, manager = login(client, "employee"), login(client, "hr"), login(client, "manager")
    client.post("/api/feedback/ratings", headers=employee, json={
        "clarity": 1, "usefulness": 1, "comment": "This is unfair and my manager rated me down.",
        "flagged": [{"feature": f, "kind": "unfair"} for f in ("performance_score", "manager_rating", "leadership_score")]})
    fields = {f["name"]: f["current"] for f in client.get("/api/feedback/fields", headers=employee).json()}
    pending = client.post("/api/feedback/corrections", headers=employee, json={
        "field": "manager_rating", "requested_value": 5, "note": "My manager's rating was entered wrongly."}).json()
    rejected = client.post("/api/feedback/corrections", headers=employee, json={
        "field": "late_days", "requested_value": max(fields["late_days"] - 1, 0) if fields["late_days"] else 1,
        "note": "Two of those late days were a train strike."}).json()
    client.post(f"/api/hr/feedback/corrections/{rejected['id']}/reject", headers=hr,
                json={"reason": "The attendance system shows these days as late."})
    nomination = client.post("/api/promotion/nominations", headers=manager, json=recommendation(person)).json()
    client.post(f"/api/hr/feedback/nominations/{nomination['id']}/defer", headers=hr)
    assert pending["status"] == "pending"

    texts = {"biased_rating": "Mo Manager rated Eli Employee far below the work they actually delivered this year.",
             "favouritism": "Mo Manager gives the best projects to friends, never to Eli Employee.",
             "discrimination": "I believe my appraisal was marked down because of who I am, not my work.",
             "wrong_record": "My training hours are missing from the record the promotion model uses."}
    for category, text in texts.items():
        # As a reporter does: the anonymiser's version is what gets sent (names become [PERSON 1] and so on)
        cleaned = client.post("/api/reports/preview", headers=employee, json={"text": text}).json()["text"]
        case = client.post("/api/reports", headers=employee, json={"category": category, "text": cleaned}).json()
        client.post(f"/api/hr/reports/{case['case_id']}/messages", headers=hr, json={"text": "Thank you, we are looking into it."})
        client.post("/api/reports/messages", headers=employee,
                    json={"case_id": case["case_id"], "key": case["key"], "text": "It happened again this month."})
        outcome = "rating_unfair" if category == "biased_rating" else "substantiated"
        client.patch(f"/api/hr/reports/{case['case_id']}", headers=hr, json={"outcome": outcome, "status": "closed"})


def test_feedback_and_reports_never_change_a_prediction_but_a_confirmed_correction_does(client):
    person = employee_id(client)
    before = prediction_bytes(client, person)
    add_every_kind_of_feedback_and_report(client, person)
    after = prediction_bytes(client, person)
    for name in before:
        assert after[name] == before[name], f"{name} changed after feedback and reports"

    # The only way feedback changes a prediction: HR confirms a correction to the record
    hr = login(client, "hr")
    pending = next(r for r in client.get("/api/hr/feedback/corrections", headers=hr).json() if r["status"] == "pending")
    client.post(f"/api/hr/feedback/corrections/{pending['id']}/confirm", headers=hr, json={"verified_value": 5})
    corrected = prediction_bytes(client, person)
    assert corrected["explanation (HR)"] != before["explanation (HR)"]
    [change] = client.get(f"/api/promotion/records/{person}/history", headers=hr).json()
    assert change["source"] == "correction" and change["changes"][0]["field"] == "manager_rating"
    assert change["score_before"] != change["score_after"]
    log = client.get("/api/admin/activity", headers=login(client, "admin"), params={"action": "correction_confirmed"}).json()
    assert len(log["entries"]) == 1


def test_the_promotion_code_never_imports_or_names_feedback_or_reports():
    """A static check over every file in app/promotion: imports, table names and model names."""
    forbidden_names = FEEDBACK_AND_REPORT_TABLES | {"ExplanationRating", "CorrectionRequest", "NominationDeferral",
                                                    "Report", "Message", "Evidence"}
    for file in PROMOTION.glob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("app.feedback", "app.reporting")), f"{file.name}: {node.module}"
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith(("app.feedback", "app.reporting")) for a in node.names), file.name
            elif isinstance(node, ast.Name) and node.id in forbidden_names:
                pytest.fail(f"{file.name} uses {node.id}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                words = set(node.value.replace('"', " ").replace("'", " ").split())
                assert not words & FEEDBACK_AND_REPORT_TABLES, f"{file.name} names a feedback or report table"


def test_the_tables_checked_are_all_the_feedback_and_report_tables():
    """If a new feedback or reporting table is added, the checks above must know about it."""
    import app.feedback.models  # noqa: F401
    import app.reporting.models  # noqa: F401
    owned = {t.name for t in Base.metadata.sorted_tables
             if any(m in t.name for m in ("rating", "correction", "deferral", "report"))}
    assert owned == FEEDBACK_AND_REPORT_TABLES


def test_the_prediction_endpoints_run_no_sql_on_feedback_or_report_tables(client):
    person = employee_id(client)
    add_every_kind_of_feedback_and_report(client, person)
    statements = []
    listener = lambda conn, cursor, statement, *args: statements.append(statement.lower())  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        prediction_bytes(client, person)
        hr = login(client, "hr")
        client.post(f"/api/promotion/employees/{person}/predict", headers=hr)
        client.post(f"/api/promotion/employees/{person}/lime", headers=hr)
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert statements, "no SQL was captured"
    for statement in statements:
        for table in FEEDBACK_AND_REPORT_TABLES:
            assert f" {table}" not in statement and f'"{table}"' not in statement, statement[:120]
