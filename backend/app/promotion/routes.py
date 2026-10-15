"""
Promotion prediction API.

Who sees what (checked here, on every request):
- HR: every employee
- Manager: their own team, a team they cover for while its manager is away, and (read-only) everyone further down
  their reporting line (teams.py)
- Employee: only themselves
- Admin: none of it (admins manage accounts, not promotions), unless an admin has given them
  "can view employee data": then they see everyone, read-only (they can't nominate, decide or edit)
- Auditor: no individual employees; the model's overall importance (and the decision log, in
  routes_decisions.py)
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import jobs
from app.core.database import get_promotion_db as get_db  # the promotion code's own (restricted) connection
from app.core.roles import ADMIN, AUDITOR, EMPLOYEE, HR, MANAGER
from app.core.security import get_current_user
from app.promotion import cycles, teams
from app.promotion.explain import ModelNotTrained, get_model
from app.promotion.features import EXCLUDED
from app.promotion.models import Employee

router = APIRouter(prefix="/api/promotion", tags=["promotion"])


def may_view_all(user: User) -> bool:
    """HR, and admins who were given the permission, see every employee."""
    return user.role == HR or (user.role == ADMIN and bool(user.can_view_employees))


def promotion_roles(user: User = Depends(get_current_user)) -> User:
    """Who may use the promotion pages: employees, managers, HR, and admins with the permission."""
    if user.role in (HR, MANAGER, EMPLOYEE) or may_view_all(user):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not have access to this.")


def can_see(user: User, employee: Employee, db: Session) -> bool:
    """The access rule in one place."""
    if may_view_all(user):
        return True
    if user.role == MANAGER:
        return employee.id in teams.team_of(db, user)
    return user.role == EMPLOYEE and user.employee_id == employee.id


def visible_employee(employee_id: int, user: User, db: Session) -> Employee:
    """Load an employee the user may see, or refuse."""
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    if not can_see(user, employee, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only see your own record, or your team's if you're a manager.")
    return employee


def model():
    """The live model, or a clear message if it hasn't been trained yet."""
    try:
        return get_model()
    except ModelNotTrained as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error))


def scored_employees(user: User, db: Session) -> dict:
    """
    The employees this user may see, each with their readiness score: the saved score when a review cycle is open
    (`cycle` says which), otherwise worked out by the live model now (everyone in one call).
    """
    query = select(Employee).order_by(Employee.full_name)
    relation = {}
    if user.role == MANAGER:
        relation = teams.team_of(db, user)
        query = query.where(Employee.id.in_(relation))
    elif user.role == EMPLOYEE:
        query = query.where(Employee.id == (user.employee_id or -1))
    live = model()
    employees = list(db.scalars(query))
    cycle = cycles.open_cycle(db)
    if cycle is not None:
        saved = cycles.scores_for(db, cycle, employees, live)
        rows = [{"id": e.id, "full_name": e.full_name, "department": e.department,
                 "score": saved[e.id].score, "recommended": saved[e.id].recommended} for e in employees]
        result = {"threshold": cycle.threshold, "model_version": cycle.model_version, "employees": rows,
                  "cycle": cycles.summary(cycle)}
    else:
        rows = [{"id": e.id, "full_name": e.full_name, "department": e.department,
                 "score": round(score, 4), "recommended": score >= live.threshold}
                for e, score in zip(employees, live.scores([e.record for e in employees]))]
        result = {"threshold": live.threshold, "model_version": live.version, "employees": rows, "cycle": None}
    if user.role == MANAGER:  # how each person relates to this manager, and who manages anyone not on their own team
        names = {u.id: u.full_name for u in db.scalars(select(User).where(
            User.id.in_({e.manager_user_id for e in employees if e.manager_user_id})))}
        for row, e in zip(rows, employees):
            row["relation"] = relation[e.id]
            row["manager"] = names.get(e.manager_user_id) if relation[e.id] != teams.DIRECT else None
    return result


@router.get("/employees")
def list_employees(user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The employees this user may see, each with their readiness score."""
    return scored_employees(user, db)


@router.post("/employees/predict-all")
def predict_all(user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """
    "Run predictions for everyone": score every employee this user may see with the live model, now, and say when.
    Nothing is saved: the scores are worked out from the current records each time.
    """
    return {**scored_employees(user, db), "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


@router.get("/employees/{employee_id}")
def explain_employee(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """
    Score, exact contributions (SHAP), plain-language summary and the what-if options, at once. LIME's rules are
    included when they're already worked out for this record; otherwise "lime" is empty (start it with
    POST /employees/{id}/lime).
    """
    employee = visible_employee(employee_id, user, db)
    live = model()
    state = jobs.state(lime_key(live.version, employee.record)) or {}
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
            **live.explain(employee.record, with_lime=False),
            "lime": state.get("result") if state.get("status") == "done" else None}


class WhatIfIn(BaseModel):
    changes: dict[str, float]


@router.get("/employees/{employee_id}/profile")
def profile(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """Who the employee is, without running the model (the page shows this before "Run prediction" is clicked)."""
    employee = visible_employee(employee_id, user, db)
    live = model()
    cover = teams.cover_for(db, employee.manager_user_id)
    relation = teams.team_of(db, user).get(employee.id) if user.role == MANAGER else None
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
            "model": live.info["model"], "trained_at": live.info["trained_at"],
            "manager": teams.manager_name(db, employee),
            "cover": {"name": db.get(User, cover.cover_user_id).full_name, "until": cover.ends.isoformat()} if cover else None,
            "relation": relation, "may_nominate": relation in teams.MAY_NOMINATE}


@router.post("/employees/{employee_id}/predict")
def predict(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """
    Run the model now: the score and each factor's exact contribution, the summary and the what-if options.
    The page calls this when someone clicks "Run prediction"; LIME and the tips follow as separate steps.
    """
    employee = visible_employee(employee_id, user, db)
    live = model()
    started = time.perf_counter()
    result = live.explain(employee.record, with_lime=False)
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department, **result,
            "trained_at": live.info["trained_at"], "duration_ms": round((time.perf_counter() - started) * 1000)}


# ─── LIME, in the background ──────────────────────────────────────────────────
# LIME asks the model 2,000 times per employee, so it runs as a background job (app/core/jobs.py) instead of
# holding up the request. A result is kept under the model version and the exact record, so a corrected record or
# a newly released model never gets an old answer.
def lime_key(version: str, record: dict) -> str:
    fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:24]
    return f"lime:{version}:{fingerprint}"


def start_lime(live, record: dict) -> dict:
    def work():
        started = time.perf_counter()
        return {**live.lime(record), "duration_ms": round((time.perf_counter() - started) * 1000)}
    return jobs.submit(lime_key(live.version, record), work)


def warm_explanation(record: dict) -> None:
    """Start working out a changed record's second opinion now, so it's ready when someone opens the page."""
    if os.getenv("WARM_EXPLANATIONS", "1") == "1":
        try:
            start_lime(get_model(), record)
        except ModelNotTrained:
            pass


def lime_answer(state: dict | None, response: Response) -> dict:
    """Done: 200 with the result. Still working: 202 (ask again shortly). Failed: 500 with the reason."""
    if state is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LIME hasn't been started for this record yet.")
    if state["status"] == "done":
        return {"status": "done", **state["result"]}
    if state["status"] == "error":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"LIME failed: {state['error']}")
    response.status_code = status.HTTP_202_ACCEPTED
    return {"status": "running"}


@router.post("/employees/{employee_id}/lime")
def lime(employee_id: int, response: Response, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """
    The second opinion: start LIME for this employee (or get the result if it's already worked out). 200 with the
    rules and fit when ready; 202 while it runs; then ask again with GET.
    """
    employee = visible_employee(employee_id, user, db)
    return lime_answer(start_lime(model(), employee.record), response)


@router.get("/employees/{employee_id}/lime")
def lime_result(employee_id: int, response: Response, user: User = Depends(promotion_roles),
                db: Session = Depends(get_db)):
    """LIME's result for this employee's current record and the live model: 200 when ready, 202 while it runs."""
    employee = visible_employee(employee_id, user, db)
    live = model()
    return lime_answer(jobs.state(lime_key(live.version, employee.record)), response)


@router.post("/employees/{employee_id}/what-if")
def what_if(employee_id: int, body: WhatIfIn, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The score and explanation if some improvable inputs were different. Nothing is saved."""
    employee = visible_employee(employee_id, user, db)
    live = model()
    try:
        changed = live.apply_changes(employee.record, body.changes)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    result = live.explain(changed, with_lime=False)
    result["original_score"] = round(live.score(employee.record), 4)
    return result


@router.get("/employees/{employee_id}/tips")
def tips(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The smallest realistic improvements that would reach the threshold."""
    employee = visible_employee(employee_id, user, db)
    return model().tips(employee.record)


def importance_roles(user: User = Depends(get_current_user)) -> User:
    """Everyone who uses the promotion pages, plus the auditor: how the model works is not about any one person."""
    return user if user.role == AUDITOR else promotion_roles(user)


@router.get("/importance")
def importance(_: User = Depends(importance_roles)):
    """
    Which inputs matter most across all employees (measured on the training sample), and every piece of
    information the model is never given, with the reason.
    """
    live = model()
    return {"features": live.importance, "sample_size": len(live.background),
            "never_used": [{"name": name.replace("_", " "), "reason": reason} for name, reason in EXCLUDED.items()]}
