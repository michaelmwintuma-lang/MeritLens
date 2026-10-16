"""
Development plan API. The employee, their manager (and a manager covering), and HR read and change the plan; an
admin with the permission to view employees reads it. The other side is told on their bell: the employee when a
manager or HR adds a goal, the manager when the employee adds or finishes one.
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import login_for_employee
from app.accounts.models import User
from app.core import notifications
from app.core.database import get_db
from app.core.roles import ADMIN, EMPLOYEE
from app.development.models import DevelopmentGoal
from app.promotion.models import Employee
from app.promotion.routes import promotion_roles, visible_employee

router = APIRouter(prefix="/api/development", tags=["development plan"])
MAX_GOALS = 20


def describe(goal: DevelopmentGoal) -> dict:
    return {"id": goal.id, "title": goal.title, "feature": goal.feature, "target": goal.target, "note": goal.note,
            "due": goal.due.isoformat() if goal.due else None, "added_by": goal.added_by_name,
            "added_at": goal.added_at.isoformat(timespec="seconds"), "done": goal.done_at is not None,
            "done_by": goal.done_by_name, "done_at": goal.done_at.isoformat(timespec="seconds") if goal.done_at else None}


def may_change(user: User) -> None:
    if user.role == ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins can read development plans, not change them.")


def tell_other_side(db: Session, user: User, employee: Employee, text: str) -> None:
    """The employee hears about their manager's or HR's changes; the manager hears about the employee's."""
    if user.role == EMPLOYEE:
        if employee.manager_user_id:
            notifications.add(db, employee.manager_user_id, f"{employee.full_name}: {text}", f"/employees/{employee.id}#plan")
    else:
        login = login_for_employee(db, employee.id)
        if login and login.id != user.id:
            notifications.add(db, login.id, f"Your development plan: {text}", "/my-readiness#plan")


@router.get("/{employee_id}")
def plan(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """The goals, open ones first (soonest due first), then the finished ones."""
    visible_employee(employee_id, user, db)
    goals = list(db.scalars(select(DevelopmentGoal).where(DevelopmentGoal.employee_id == employee_id)))
    goals.sort(key=lambda g: (g.done_at is not None, g.due or date.max, g.id))
    return {"employee_id": employee_id, "can_change": user.role != ADMIN, "goals": [describe(g) for g in goals]}


class GoalIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    feature: str | None = Field(default=None, max_length=60)
    target: float | None = None
    note: str | None = Field(default=None, max_length=2000)
    due: date | None = None


@router.post("/{employee_id}/goals", status_code=status.HTTP_201_CREATED)
def add_goal(employee_id: int, body: GoalIn, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    employee = visible_employee(employee_id, user, db)
    may_change(user)
    open_goals = db.scalars(select(DevelopmentGoal).where(DevelopmentGoal.employee_id == employee_id,
                                                          DevelopmentGoal.done_at.is_(None))).all()
    if len(open_goals) >= MAX_GOALS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A plan holds at most {MAX_GOALS} open goals: finish or remove one first.")
    if any(g.title.strip().lower() == body.title.strip().lower() for g in open_goals):
        raise HTTPException(status.HTTP_409_CONFLICT, "This goal is already in the plan.")
    goal = DevelopmentGoal(employee_id=employee_id, title=body.title.strip(), feature=body.feature, target=body.target,
                           note=(body.note or "").strip() or None, due=body.due, added_by_name=user.full_name)
    db.add(goal)
    tell_other_side(db, user, employee, f"new goal “{goal.title}”")
    db.commit()
    return describe(goal)


def get_goal(db: Session, goal_id: int, user: User) -> tuple[DevelopmentGoal, Employee]:
    goal = db.get(DevelopmentGoal, goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such goal.")
    employee = visible_employee(goal.employee_id, user, db)
    may_change(user)
    return goal, employee


class DoneIn(BaseModel):
    done: bool


@router.patch("/goals/{goal_id}")
def tick(goal_id: int, body: DoneIn, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """Tick a goal off (or untick it)."""
    goal, employee = get_goal(db, goal_id, user)
    if body.done and goal.done_at is None:
        goal.done_at, goal.done_by_name = datetime.now(timezone.utc), user.full_name
        tell_other_side(db, user, employee, f"goal done: “{goal.title}”")
    elif not body.done:
        goal.done_at, goal.done_by_name = None, None
    db.commit()
    return describe(goal)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(goal_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    goal, _ = get_goal(db, goal_id, user)
    db.delete(goal)
    db.commit()
