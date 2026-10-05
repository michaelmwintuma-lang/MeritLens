"""
Finance: signing off the pay rise that comes with an approved promotion.

When HR approves a promotion, its pay rise waits here. Finance either signs it off (then the manager and the
employee are told, and the employee sees the promotion) or sends it back to HR with a reason (at least 20
characters); HR revises it and resubmits it. Every step is kept (the PayReview table), and nothing is deleted.

Finance sees only what a pay decision needs: who, which department, the new role and start date, the pay rise
(and the manager's proposal), the pay policy, and HR's reason if the rise is outside the policy. Finance does NOT
see the model's score, the manager's ratings or the reasons for the promotion: those are HR's decision.
Only percentages are handled, never salaries.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import hr_contacts
from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_db
from app.core.roles import FINANCE
from app.core.security import require_roles
from app.promotion.models import Decision, Employee, Nomination, PayReview
from app.promotion.routes_decisions import MIN_DISAGREEMENT_REASON, name_of, pay_history, pay_policy, tell_about_promotion

router = APIRouter(prefix="/api/finance", tags=["finance"])
finance_only = require_roles(FINANCE)
STATUSES = ("awaiting_finance", "returned", "signed_off")


def review_row(db: Session, decision: Decision, policy) -> dict:
    """One pay rise as Finance sees it."""
    employee = db.get(Employee, decision.employee_id)
    nomination = db.get(Nomination, decision.nomination_id)
    within = policy.min_raise <= (decision.approved_raise or 0) <= policy.max_raise
    return {
        "id": decision.id,
        "employee": {"full_name": employee.full_name, "department": employee.department},
        "new_title": nomination.proposed_title,
        "start": nomination.proposed_start.isoformat() if nomination.proposed_start else None,
        "proposed_raise": nomination.proposed_raise,         # what the manager proposed
        "raise": decision.approved_raise,                    # what HR approved
        "within_policy": within,
        "raise_reason": decision.raise_reason,               # HR's reason when outside the policy
        "approved_by": name_of(db, decision.decided_by),
        "approved_on": decision.decided_at.date().isoformat(),
        "status": decision.pay_status,
        "history": pay_history(db, decision.id),
    }


@router.get("/pay-reviews")
def pay_reviews(db: Session = Depends(get_db), _: User = Depends(finance_only)):
    """Every promotion pay rise that has been through Finance (waiting first, then newest), with a summary."""
    policy = pay_policy(db)
    decisions = db.scalars(select(Decision).where(Decision.pay_status.in_(STATUSES))).all()
    order = {"awaiting_finance": 0, "returned": 1, "signed_off": 2}
    decisions.sort(key=lambda d: (order[d.pay_status], -d.decided_at.timestamp()))
    rows = [review_row(db, d, policy) for d in decisions]

    year = datetime.now(timezone.utc).year
    signed = [r for r in rows if r["status"] == "signed_off" and any(
        h["action"] == "signed_off" and h["at"].startswith(str(year)) for h in r["history"])]
    by_department = {}
    for r in signed:
        dep = by_department.setdefault(r["employee"]["department"], [])
        dep.append(r["raise"])
    return {
        "policy": {"min_raise": policy.min_raise, "max_raise": policy.max_raise},
        "summary": {
            "awaiting": sum(r["status"] == "awaiting_finance" for r in rows),
            "returned": sum(r["status"] == "returned" for r in rows),
            "signed_off_this_year": len(signed),
            "average_raise_this_year": round(sum(r["raise"] for r in signed) / len(signed), 1) if signed else None,
            "outside_policy_this_year": sum(not r["within_policy"] for r in signed),
            "by_department": [{"department": dep, "promotions": len(raises), "average_raise": round(sum(raises) / len(raises), 1)}
                              for dep, raises in sorted(by_department.items())],
        },
        "reviews": rows,
    }


def waiting(db: Session, decision_id: int) -> Decision:
    decision = db.get(Decision, decision_id)
    if decision is None or decision.pay_status not in STATUSES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such pay rise.")
    if decision.pay_status != "awaiting_finance":
        raise HTTPException(status.HTTP_409_CONFLICT, "This pay rise isn't waiting for Finance.")
    return decision


class SignOffIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReturnIn(BaseModel):
    note: str = Field(max_length=2000)


@router.post("/pay-reviews/{decision_id}/sign-off")
def sign_off(decision_id: int, body: SignOffIn, background: BackgroundTasks, db: Session = Depends(get_db),
             user: User = Depends(finance_only)):
    """Finance confirms the pay rise. The promotion is now final: the manager and the employee are told."""
    decision = waiting(db, decision_id)
    decision.pay_status = "signed_off"
    db.add(PayReview(decision_id=decision.id, action="signed_off", by_user=user.id, by_name=user.full_name,
                     raise_percent=decision.approved_raise, note=(body.note or "").strip() or None))
    employee_name = db.get(Employee, decision.employee_id).full_name
    record(db, user, "pay_signed_off", f"{employee_name}: {decision.approved_raise:g}%")
    db.commit()
    tell_about_promotion(background, db, decision)
    return review_row(db, decision, pay_policy(db))


@router.post("/pay-reviews/{decision_id}/return")
def send_back(decision_id: int, body: ReturnIn, background: BackgroundTasks, db: Session = Depends(get_db),
              user: User = Depends(finance_only)):
    """Finance sends the pay rise back to HR with a reason. Nobody else is told."""
    note = body.note.strip()
    if len(note) < MIN_DISAGREEMENT_REASON:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Please tell HR why, in at least {MIN_DISAGREEMENT_REASON} characters.")
    decision = waiting(db, decision_id)
    decision.pay_status = "returned"
    db.add(PayReview(decision_id=decision.id, action="returned", by_user=user.id, by_name=user.full_name,
                     raise_percent=decision.approved_raise, note=note))
    employee_name = db.get(Employee, decision.employee_id).full_name
    record(db, user, "pay_returned", employee_name)
    db.commit()
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.pay_returned(hr_name, employee_name, user.full_name, note))
    return review_row(db, decision, pay_policy(db))


@router.get("/pay-policy")
def read_pay_policy(db: Session = Depends(get_db), _: User = Depends(finance_only)):
    """The range HR set (Finance can read it, not change it)."""
    policy = pay_policy(db)
    return {"min_raise": policy.min_raise, "max_raise": policy.max_raise}
