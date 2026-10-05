"""
Nominations and decisions.

1. A manager nominates someone on their team, with a short reason.
2. HR reviews the nomination alongside the model's score and explanation, and approves or rejects it.
   The model only advises: HR's decision is final. If HR disagrees with the model, a reason of at least
   20 characters is required.
3. Every decision is saved in the decision log, with the model's score and recommendation at that moment.
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import HR, MANAGER
from app.core.security import require_roles
from app.promotion.models import Decision, Employee, Nomination
from app.promotion.routes import model
from app.core.activity import record
from app.accounts.contacts import hr_contacts, login_for_employee
from app.core import email_templates as templates
from app.core import mailer

router = APIRouter(prefix="/api/promotion", tags=["decisions"])
MIN_DISAGREEMENT_REASON = 20


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def name_of(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    return user.full_name if user else "unknown"


# ─── Nominating ───────────────────────────────────────────────────────────────
class NominationIn(BaseModel):
    employee_id: int
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/nominations", status_code=status.HTTP_201_CREATED)
def nominate(body: NominationIn, background: BackgroundTasks, user: User = Depends(require_roles(MANAGER)),
             db: Session = Depends(get_db)):
    """A manager nominates one of their own team members."""
    employee = db.get(Employee, body.employee_id)
    if employee is None or employee.manager_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only nominate people on your own team.")
    if db.scalar(select(Nomination).where(Nomination.employee_id == employee.id, Nomination.status == "pending")):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{employee.full_name} already has a nomination waiting for HR.")
    nomination = Nomination(employee_id=employee.id, nominated_by=user.id, reason=body.reason.strip())
    db.add(nomination)
    record(db, user, "nomination_made", employee.full_name)
    db.commit()
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.nomination_received(hr_name, employee.full_name, user.full_name))
    return {"id": nomination.id, "status": nomination.status}


def describe(db: Session, nomination: Nomination) -> dict:
    """A nomination as the pages show it, with the model's current view and the decision, if any."""
    employee = db.get(Employee, nomination.employee_id)
    live = model()
    score = live.score(employee.record)
    decision = db.scalar(select(Decision).where(Decision.nomination_id == nomination.id))
    return {
        "id": nomination.id,
        "employee": {"id": employee.id, "full_name": employee.full_name, "department": employee.department},
        "nominated_by": name_of(db, nomination.nominated_by),
        "reason": nomination.reason,
        "status": nomination.status,
        "created_at": iso(nomination.created_at),
        "model_now": {"score": round(score, 4), "threshold": live.threshold, "recommended": score >= live.threshold},
        "decision": log_entry(db, decision) if decision else None,
    }


@router.get("/nominations")
def list_nominations(user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """HR sees every nomination; a manager sees the ones they made. Newest first."""
    query = select(Nomination).order_by(Nomination.created_at.desc())
    if user.role == MANAGER:
        query = query.where(Nomination.nominated_by == user.id)
    return [describe(db, n) for n in db.scalars(query)]


@router.get("/nominations/{nomination_id}")
def get_nomination(nomination_id: int, user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    nomination = db.get(Nomination, nomination_id)
    if nomination is None or (user.role == MANAGER and nomination.nominated_by != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such nomination.")
    return describe(db, nomination)


# ─── Deciding ─────────────────────────────────────────────────────────────────
class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=2000)


@router.post("/nominations/{nomination_id}/decision", status_code=status.HTTP_201_CREATED)
def decide(nomination_id: int, body: DecisionIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)),
           db: Session = Depends(get_db)):
    """HR approves or rejects. Disagreeing with the model needs a reason of at least 20 characters."""
    nomination = db.get(Nomination, nomination_id)
    if nomination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such nomination.")
    if nomination.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This nomination has already been decided.")

    # What the model says right now, recorded with the decision
    live = model()
    score = live.score(db.get(Employee, nomination.employee_id).record)
    recommended = score >= live.threshold
    agrees = (body.decision == "approve") == recommended
    reason = (body.reason or "").strip() or None
    if not agrees and (reason is None or len(reason) < MIN_DISAGREEMENT_REASON):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"You are disagreeing with the model, so please give a reason of at least "
                            f"{MIN_DISAGREEMENT_REASON} characters.")

    decision = Decision(nomination_id=nomination.id, employee_id=nomination.employee_id, decided_by=user.id,
                        decision=body.decision, model_score=round(score, 4), model_threshold=live.threshold,
                        model_recommended=recommended, agrees_with_model=agrees, reason=reason)
    nomination.status = "approved" if body.decision == "approve" else "rejected"
    db.add(decision)
    employee_name = db.get(Employee, nomination.employee_id).full_name
    record(db, user, "decision_made", f"{nomination.status}: {employee_name}{'' if agrees else ' (differs from the model)'}")
    db.commit()
    approved = body.decision == "approve"
    manager = db.get(User, nomination.nominated_by)
    if manager and manager.email:
        background.add_task(mailer.send, manager.email, templates.decision_for_manager(manager.full_name, employee_name, approved, reason))
    employee_login = login_for_employee(db, nomination.employee_id) if approved else None
    if employee_login and employee_login.email:
        background.add_task(mailer.send, employee_login.email, templates.promotion_approved(employee_login.full_name))
    return log_entry(db, decision)


# ─── The decision log ─────────────────────────────────────────────────────────
def log_entry(db: Session, decision: Decision) -> dict:
    employee = db.get(Employee, decision.employee_id)
    return {
        "id": decision.id,
        "nomination_id": decision.nomination_id,
        "employee": {"id": employee.id, "full_name": employee.full_name, "department": employee.department},
        "decision": decision.decision,
        "decided_by": name_of(db, decision.decided_by),
        "decided_at": iso(decision.decided_at),
        "model_score": decision.model_score,
        "model_threshold": decision.model_threshold,
        "model_recommended": decision.model_recommended,
        "agrees_with_model": decision.agrees_with_model,
        "reason": decision.reason,
    }


@router.get("/decisions")
def decision_log(_: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """Every decision, newest first."""
    return [log_entry(db, d) for d in db.scalars(select(Decision).order_by(Decision.decided_at.desc(), Decision.id.desc()))]
