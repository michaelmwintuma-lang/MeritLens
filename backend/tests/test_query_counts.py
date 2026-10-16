"""
Lists ask the database a fixed number of times, however long they are (no "N+1": one query per row). The full
measurement with 5,000 employees is evaluation/load_test.py (results/load_test.json).
"""
from sqlalchemy import event, select

from app.accounts.models import User
from app.core.database import SessionLocal, engine
from app.promotion.models import Decision, Employee, Nomination
from tests.conftest import login


def add_decided(count: int, start: int) -> None:
    with SessionLocal() as db:
        manager = db.scalar(select(User).where(User.username == "manager"))
        hr = db.scalar(select(User).where(User.username == "hr"))
        for i, employee_id in enumerate(db.scalars(select(Employee.id).order_by(Employee.id).offset(start).limit(count))):
            nomination = Nomination(employee_id=employee_id, nominated_by=manager.id, reason="Test.", status="approved")
            db.add(nomination)
            db.flush()
            db.add(Decision(nomination_id=nomination.id, employee_id=employee_id, decided_by=hr.id, decision="approve",
                            model_score=0.5, model_threshold=0.4, model_recommended=True, agrees_with_model=True,
                            approved_raise=8.0, pay_status="signed_off" if i % 2 else "awaiting_finance"))
        db.commit()


def queries_for(client, path: str, headers: dict) -> int:
    count = [0]
    def counter(*_):
        count[0] += 1
    event.listen(engine, "before_cursor_execute", counter)
    try:
        assert client.get(path, headers=headers).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", counter)
    return count[0]


def test_lists_make_the_same_number_of_queries_for_4_rows_or_40(client):
    pages = {"/api/promotion/nominations": login(client, "hr"), "/api/promotion/decisions": login(client, "hr"),
             "/api/finance/pay-reviews": login(client, "finance"), "/api/finance/payroll.csv?include_sent=true": login(client, "finance")}
    add_decided(4, 0)
    for path, headers in pages.items():  # first visits set things up once (e.g. the pay policy): not counted
        client.get(path, headers=headers)
    few = {path: queries_for(client, path, headers) for path, headers in pages.items()}
    add_decided(36, 4)
    many = {path: queries_for(client, path, headers) for path, headers in pages.items()}
    assert many == few
