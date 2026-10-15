"""
Review cycles API (see cycles.py for how a cycle works).

- HR opens and closes cycles, follows each one's progress (with the people it concerns) and exports it as CSV.
- The compliance auditor follows the same pages read-only, with totals only: never a named person.
- Everyone signed in can ask which cycle is open (its name and nomination deadline), for their pages.
- An employee's scores over the cycles: the employee themselves, their manager, and HR (as for any score).
"""
import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_promotion_db as get_db  # the promotion code's own (restricted) connection
from app.core.roles import AUDITOR, HR, MANAGER
from app.core.security import get_current_user, require_roles
from app.promotion import cycles
from app.promotion.models import CycleScore, Decision, Employee, Nomination, ReviewCycle
from app.promotion.routes import model, promotion_roles, visible_employee

router = APIRouter(prefix="/api/promotion", tags=["review cycles"])


def get_cycle(db: Session, cycle_id: int) -> ReviewCycle:
    cycle = db.get(ReviewCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such review cycle.")
    return cycle


@router.get("/cycles/current")
def current_cycle(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The open cycle's name, model and nomination deadline, or null. For every signed-in page."""
    cycle = cycles.open_cycle(db)
    return {"cycle": cycles.summary(cycle) if cycle else None}


@router.get("/cycles")
def list_cycles(_: User = Depends(require_roles(HR, AUDITOR)), db: Session = Depends(get_db)):
    """Every cycle, newest first, each with its headline totals."""
    rows = []
    for cycle in db.scalars(select(ReviewCycle).order_by(ReviewCycle.id.desc())):
        totals = cycles.progress(db, cycle, with_people=False)["totals"]
        rows.append({**cycles.summary(cycle), "people": totals["people"], "recommended": totals["recommended"],
                     "nominated": totals["nominated"], "approved": totals["approved"]})
    return rows


class CycleIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    nominations_close: date | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.post("/cycles", status_code=status.HTTP_201_CREATED)
def open_cycle(body: CycleIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)),
               db: Session = Depends(get_db)):
    """HR opens a cycle: everyone is scored with the live model now, and the scores are saved. One at a time."""
    if (current := cycles.open_cycle(db)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"“{current.name}” is still open. Close it before opening another.")
    if body.nominations_close is not None and not date.today() <= body.nominations_close <= date.today() + timedelta(days=366):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The nomination deadline must be between today and a year from now.")
    name = body.name.strip()
    if db.scalar(select(ReviewCycle).where(ReviewCycle.name == name)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"There is already a cycle called “{name}”.")
    cycle = cycles.open_new(db, model(), user, name, body.nominations_close, (body.note or "").strip() or None)
    record(db, user, "cycle_opened", name)
    db.commit()
    tell_managers(background, db, cycle)
    return cycles.progress(db, cycle, with_people=True)


def tell_managers(background: BackgroundTasks, db: Session, cycle: ReviewCycle) -> None:
    """Email each manager with a team: the cycle is open, how many of their team the model recommends, the deadline."""
    team_scores: dict[int, list[CycleScore]] = {}
    for score, employee in db.execute(select(CycleScore, Employee).join(Employee, Employee.id == CycleScore.employee_id)
                                      .where(CycleScore.cycle_id == cycle.id, Employee.manager_user_id.is_not(None))):
        team_scores.setdefault(employee.manager_user_id, []).append(score)
    for manager_id, scores in team_scores.items():
        manager = db.get(User, manager_id)
        if manager and manager.is_active and manager.role == MANAGER and manager.email:
            background.add_task(mailer.send, manager.email, templates.cycle_opened(
                manager.full_name, cycle.name, len(scores), sum(1 for s in scores if s.recommended),
                cycle.nominations_close.isoformat() if cycle.nominations_close else None))


@router.get("/cycles/{cycle_id}")
def cycle_progress(cycle_id: int, user: User = Depends(require_roles(HR, AUDITOR)), db: Session = Depends(get_db)):
    """How a cycle is going. HR sees the people it concerns; the auditor sees totals only."""
    return cycles.progress(db, get_cycle(db, cycle_id), with_people=user.role == HR)


@router.post("/cycles/{cycle_id}/close")
def close_cycle(cycle_id: int, user: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """HR closes the open cycle, once every nomination in it has been decided."""
    cycle = get_cycle(db, cycle_id)
    try:
        cycles.close(db, cycle, user)
    except ValueError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error))
    record(db, user, "cycle_closed", cycle.name)
    db.commit()
    return cycles.progress(db, cycle, with_people=True)


@router.get("/cycles/{cycle_id}/export.csv")
def export_cycle(cycle_id: int, _: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """HR: one row per employee in the cycle: their saved score, and what happened to any nomination."""
    cycle = get_cycle(db, cycle_id)
    nominations = {n.employee_id: n for n in db.scalars(select(Nomination).where(Nomination.cycle_id == cycle.id))}
    decisions = {d.nomination_id: d for d in db.scalars(select(Decision).where(Decision.cycle_id == cycle.id))}
    managers = {u.id: u.full_name for u in db.scalars(select(User))}
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["employee_id", "full_name", "department", "manager", "readiness_score", "recommended",
                     "score_at_opening", "changed_by_record_correction_or_edit", "nominated", "proposed_title",
                     "decision", "agrees_with_model", "approved_raise_percent"])
    rows = db.execute(select(CycleScore, Employee).join(Employee, Employee.id == CycleScore.employee_id)
                      .where(CycleScore.cycle_id == cycle.id).order_by(Employee.full_name))
    for score, employee in rows:
        nomination = nominations.get(employee.id)
        decision = decisions.get(nomination.id) if nomination else None
        writer.writerow([employee.id, employee.full_name, employee.department, managers.get(employee.manager_user_id, ""),
                         score.score, "yes" if score.recommended else "no",
                         "" if score.score_at_opening is None else score.score_at_opening,
                         "yes" if score.record_change_id else "no", "yes" if nomination else "no",
                         nomination.proposed_title if nomination else "",
                         decision.decision if decision else ("waiting" if nomination else ""),
                         ("yes" if decision.agrees_with_model else "no") if decision else "",
                         decision.approved_raise if decision and decision.approved_raise is not None else ""])
    filename = "".join(ch if ch.isalnum() else "-" for ch in cycle.name).strip("-").lower() or f"cycle-{cycle.id}"
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="review-cycle-{filename}.csv"'})


@router.get("/employees/{employee_id}/trend")
def score_trend(employee_id: int, user: User = Depends(promotion_roles), db: Session = Depends(get_db)):
    """One employee's saved score in every review cycle, oldest first: to them, their manager and HR."""
    visible_employee(employee_id, user, db)
    return cycles.trend(db, employee_id)
