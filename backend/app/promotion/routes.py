"""
Promotion prediction API.

Who sees what (checked here, on every request):
- HR: every employee
- Manager: only their own team
- Employee: only themselves
- Admin: none of it (admins manage accounts, not promotions), unless an admin has given them
  "can view employee data": then they see everyone, read-only (they can't nominate, decide or edit)
- Auditor: no individual employees; the model's overall importance (and the decision log, in
  routes_decisions.py)
"""
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import ADMIN, AUDITOR, EMPLOYEE, HR, MANAGER
from app.core.security import get_current_user
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


def can_see(user: User, employee: Employee) -> bool:
    """The access rule in one place."""
    if may_view_all(user):
        return True
    if user.role == MANAGER:
        return employee.manager_user_id == user.id
    return user.role == EMPLOYEE and user.employee_id == employee.id


def visible_employee(employee_id: int, user: User, db: Session) -> Employee:
    """Load an employee the user may see, or refuse."""
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    if not can_see(user, employee):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only see your own record, or your team's if you're a manager.")
    return employee


def model():
    """The live model, or a clear message if it hasn't been trained yet."""
    try:
        return get_model()
    except ModelNotTrained as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error))


@router.get("/employees")
def list_employees(user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The employees this user may see, each with their readiness score."""
    query = select(Employee).order_by(Employee.full_name)
    if user.role == MANAGER:
        query = query.where(Employee.manager_user_id == user.id)
    elif user.role == EMPLOYEE:
        query = query.where(Employee.id == (user.employee_id or -1))
    live = model()
    employees = list(db.scalars(query))
    rows = [{"id": e.id, "full_name": e.full_name, "department": e.department,
             "score": round(score, 4), "recommended": score >= live.threshold}
            for e, score in zip(employees, live.scores([e.record for e in employees]))]  # scored all at once
    return {"threshold": live.threshold, "employees": rows}


@router.get("/employees/{employee_id}")
def explain_employee(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """Score, exact contributions (SHAP), LIME rules, plain-language summary and the what-if options."""
    employee = visible_employee(employee_id, user, db)
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
            **model().explain(employee.record)}


class WhatIfIn(BaseModel):
    changes: dict[str, float]


@router.get("/employees/{employee_id}/profile")
def profile(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """Who the employee is, without running the model (the page shows this before "Run prediction" is clicked)."""
    employee = visible_employee(employee_id, user, db)
    live = model()
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
            "model": live.info["model"], "trained_at": live.info["trained_at"]}


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


@router.post("/employees/{employee_id}/lime")
def lime(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The second opinion: LIME's rules and fit for this employee."""
    employee = visible_employee(employee_id, user, db)
    started = time.perf_counter()
    result = model().lime(employee.record)
    return {**result, "duration_ms": round((time.perf_counter() - started) * 1000)}


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
