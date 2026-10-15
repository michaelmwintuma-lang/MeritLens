"""
Finance: signing off the pay rise that comes with an approved promotion.

When HR approves a promotion, its pay rise waits here. Finance either signs it off (then the manager and the
employee are told, and the employee sees the promotion) or sends it back to HR with a reason (at least 20
characters); HR revises it and resubmits it. Every step is kept (the PayReview table), and nothing is deleted.

Finance sees only what a pay decision needs: who, which department, the new role and start date, the pay rise
(and the manager's proposal), the pay policy, and HR's reason if the rise is outside the policy. Finance does NOT
see the model's score, the manager's ratings or the reasons for the promotion: those are HR's decision.
Only percentages are handled, never salaries.

To keep the work moving: how many working days each pay rise has waited; signing off several within-policy rises
at once (each still logged on its own); a filter and totals per review cycle; and the hand-over to payroll: a CSV
of signed-off rises, then "mark as sent", so each is applied once and none is forgotten.
"""
import csv
import io
from collections import Counter
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import hr_contacts
from app.accounts.models import User
from app.core import audit
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_promotion_db as get_db  # the promotion code's own (restricted) connection
from app.core.dates import working_days_between
from app.core.roles import FINANCE
from app.core.security import require_roles
from app.promotion.models import Decision, Employee, Nomination, PayReview, ReviewCycle
from app.promotion.routes_decisions import MIN_DISAGREEMENT_REASON, name_of, pay_history, pay_policy, tell_about_promotion

router = APIRouter(prefix="/api/finance", tags=["finance"])
finance_only = require_roles(FINANCE)
STATUSES = ("awaiting_finance", "returned", "signed_off")


def review_row(db: Session, decision: Decision, policy) -> dict:
    """One pay rise as Finance sees it."""
    employee = db.get(Employee, decision.employee_id)
    nomination = db.get(Nomination, decision.nomination_id)
    within = policy.min_raise <= (decision.approved_raise or 0) <= policy.max_raise
    history = pay_history(db, decision.id)
    reached = [h for h in history if h["action"] in ("submitted", "resubmitted")]
    since = datetime.fromisoformat(reached[-1]["at"]).date() if reached else decision.decided_at.date()
    cycle = db.get(ReviewCycle, decision.cycle_id) if decision.cycle_id else None
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
        "history": history,
        # Waiting for Finance since the rise last reached Finance (working days)
        "waiting_since": since.isoformat() if decision.pay_status == "awaiting_finance" else None,
        "waiting_days": working_days_between(since, date.today()) if decision.pay_status == "awaiting_finance" else None,
        "cycle": {"id": cycle.id, "name": cycle.name} if cycle else None,
        "payroll_sent_at": decision.payroll_sent_at.date().isoformat() if decision.payroll_sent_at else None,
    }


@router.get("/pay-reviews")
def pay_reviews(cycle_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(finance_only)):
    """
    Every promotion pay rise that has been through Finance (waiting first, oldest waiting first; then newest), with
    a summary. `cycle_id` keeps only one review cycle's.
    """
    policy = pay_policy(db)
    query = select(Decision).where(Decision.pay_status.in_(STATUSES))
    if cycle_id is not None:
        query = query.where(Decision.cycle_id == cycle_id)
    decisions = db.scalars(query).all()
    order = {"awaiting_finance": 0, "returned": 1, "signed_off": 2}
    rows = [review_row(db, d, policy) for d in decisions]
    # Waiting for Finance first, longest waiting first; then sent back, then signed off, newest first within each
    waiting_rows = sorted((r for r in rows if r["status"] == "awaiting_finance"), key=lambda r: -(r["waiting_days"] or 0))
    others = sorted((r for r in rows if r["status"] != "awaiting_finance"), key=lambda r: r["approved_on"], reverse=True)
    others.sort(key=lambda r: order[r["status"]])  # a stable sort keeps newest first within each status
    rows = waiting_rows + others

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
            # Every signed-off rise (in this view), counted by percentage: how the rises spread across the policy band
            "distribution": [{"raise": value, "count": count, "within_policy": policy.min_raise <= value <= policy.max_raise}
                             for value, count in sorted(Counter(r["raise"] for r in rows if r["status"] == "signed_off").items())],
            "payroll_waiting": sum(r["status"] == "signed_off" and r["payroll_sent_at"] is None for r in rows),
            "waiting_longest": max((r["waiting_days"] for r in rows if r["waiting_days"] is not None), default=None),
        },
        "cycles": [{"id": c.id, "name": c.name} for c in db.scalars(select(ReviewCycle).where(
            ReviewCycle.id.in_(select(Decision.cycle_id).where(Decision.pay_status.in_(STATUSES)))).order_by(ReviewCycle.id.desc()))],
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


def record_sign_off(db: Session, decision: Decision, user: User, note: str | None) -> None:
    """Sign off one pay rise: its step, the audit trail and the activity log. The caller commits."""
    decision.pay_status = "signed_off"
    db.add(PayReview(decision_id=decision.id, action="signed_off", by_user=user.id, by_name=user.full_name,
                     raise_percent=decision.approved_raise, note=(note or "").strip() or None))
    audit.append(db, "pay_signed_off", user, "decision", decision.id, {"raise_percent": decision.approved_raise})
    employee_name = db.get(Employee, decision.employee_id).full_name
    record(db, user, "pay_signed_off", f"{employee_name}: {decision.approved_raise:g}%")


@router.post("/pay-reviews/{decision_id}/sign-off")
def sign_off(decision_id: int, body: SignOffIn, background: BackgroundTasks, db: Session = Depends(get_db),
             user: User = Depends(finance_only)):
    """Finance confirms the pay rise. The promotion is now final: the manager and the employee are told."""
    decision = waiting(db, decision_id)
    record_sign_off(db, decision, user, body.note)
    db.commit()
    tell_about_promotion(background, db, decision)
    return review_row(db, decision, pay_policy(db))


class SignOffManyIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


@router.post("/pay-reviews/sign-off-many")
def sign_off_many(body: SignOffManyIn, background: BackgroundTasks, db: Session = Depends(get_db),
                  user: User = Depends(finance_only)):
    """
    Sign off several pay rises at once: only ones waiting for Finance and within the pay policy (a rise outside the
    policy is always reviewed on its own). Each is signed off, logged and announced exactly as if done one by one.
    """
    policy = pay_policy(db)
    decisions = [waiting(db, decision_id) for decision_id in dict.fromkeys(body.ids)]
    outside = [db.get(Employee, d.employee_id).full_name for d in decisions
               if not policy.min_raise <= (d.approved_raise or 0) <= policy.max_raise]
    if outside:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Outside the pay policy, so review on its own: {', '.join(outside)}.")
    for decision in decisions:
        record_sign_off(db, decision, user, body.note)
    db.commit()
    for decision in decisions:
        tell_about_promotion(background, db, decision)
    return {"signed_off": len(decisions)}


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
    audit.append(db, "pay_returned", user, "decision", decision.id, {"raise_percent": decision.approved_raise})
    employee_name = db.get(Employee, decision.employee_id).full_name
    record(db, user, "pay_returned", employee_name)
    db.commit()
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.pay_returned(hr_name, employee_name, user.full_name, note))
    return review_row(db, decision, pay_policy(db))


# ─── Hand-over to payroll ─────────────────────────────────────────────────────
@router.get("/payroll.csv")
def payroll_csv(include_sent: bool = False, db: Session = Depends(get_db), _: User = Depends(finance_only)):
    """Signed-off promotion pay rises for payroll (only those not yet handed over, unless include_sent)."""
    query = select(Decision).where(Decision.pay_status == "signed_off").order_by(Decision.decided_at)
    if not include_sent:
        query = query.where(Decision.payroll_sent_at.is_(None))
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["decision_id", "employee_id", "full_name", "department", "new_title", "start_date",
                     "pay_rise_percent", "signed_off_on", "review_cycle", "sent_to_payroll_on"])
    for decision in db.scalars(query):
        employee, nomination = db.get(Employee, decision.employee_id), db.get(Nomination, decision.nomination_id)
        signed = next((h["at"][:10] for h in reversed(pay_history(db, decision.id)) if h["action"] == "signed_off"), "")
        cycle = db.get(ReviewCycle, decision.cycle_id) if decision.cycle_id else None
        writer.writerow([decision.id, employee.id, employee.full_name, employee.department, nomination.proposed_title or "",
                         nomination.proposed_start.isoformat() if nomination.proposed_start else "", decision.approved_raise,
                         signed, cycle.name if cycle else "",
                         decision.payroll_sent_at.date().isoformat() if decision.payroll_sent_at else ""])
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="payroll-{date.today().isoformat()}.csv"'})


class PayrollSentIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


@router.post("/payroll/mark-sent")
def mark_sent_to_payroll(body: PayrollSentIn, db: Session = Depends(get_db), user: User = Depends(finance_only)):
    """Finance confirms these signed-off rises were handed to payroll. Each can be marked once."""
    decisions = [db.get(Decision, i) for i in dict.fromkeys(body.ids)]
    if any(d is None or d.pay_status != "signed_off" for d in decisions):
        raise HTTPException(status.HTTP_409_CONFLICT, "Only signed-off pay rises can be handed to payroll.")
    fresh = [d for d in decisions if d.payroll_sent_at is None]
    for decision in fresh:
        decision.payroll_sent_at, decision.payroll_sent_by_name = datetime.now(timezone.utc), user.full_name
        audit.append(db, "payroll_sent", user, "decision", decision.id, {"raise_percent": decision.approved_raise})
    if fresh:
        record(db, user, "payroll_sent", f"{len(fresh)} pay rise{'' if len(fresh) == 1 else 's'}")
        db.commit()
    return {"marked": len(fresh), "already": len(decisions) - len(fresh)}


@router.get("/pay-policy")
def read_pay_policy(db: Session = Depends(get_db), _: User = Depends(finance_only)):
    """The range HR set (Finance can read it, not change it)."""
    policy = pay_policy(db)
    return {"min_raise": policy.min_raise, "max_raise": policy.max_raise}
