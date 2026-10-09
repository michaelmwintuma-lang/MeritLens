"""
Nominations and decisions.

1. A manager recommends someone on their team for promotion: a proposed new role and start date, a rating and an
   example for each of four criteria (performance, leadership, skills, impact), an overall reason, and a proposed
   pay rise (a percentage within HR's pay policy). If the model doesn't recommend the person, the manager must say
   why they disagree (at least 20 characters), just as HR must.
2. HR reviews the recommendation alongside the model's score and explanation, and approves or rejects it. The
   model only advises: HR's decision is final. If HR disagrees with the model, a reason of at least 20 characters
   is required. An approval sets the final pay rise; going outside the policy range needs a written reason too.
3. Every decision is saved in the decision log, with the model's score and recommendation at that moment.
4. An approval's pay rise goes to Finance to sign off (routes_finance.py). Only when Finance signs it off are the
   manager and employee told, and the employee sees the promotion. If Finance sends it back, HR revises the rise
   and resubmits it. A rejection is final at once and goes straight to the manager.

Pay is kept apart from the model: only percentages are stored (never salaries), and they never reach the model's
inputs (tests check this).
"""
import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import finance_contacts, hr_contacts, login_for_employee
from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_db
from app.core.roles import AUDITOR, EMPLOYEE, HR, MANAGER
from app.core.security import require_roles
from app.promotion.models import Decision, Employee, Nomination, PayPolicy, PayReview
from app.promotion.routes import model

router = APIRouter(prefix="/api/promotion", tags=["decisions"])
MIN_DISAGREEMENT_REASON = 20
CRITERIA = {
    "performance": "Performance",
    "leadership": "Leadership",
    "skills": "Skills and knowledge",
    "impact": "Impact on the team and organisation",
}


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def name_of(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    return user.full_name if user else "unknown"


# ─── The pay policy ───────────────────────────────────────────────────────────
def pay_policy(db: Session) -> PayPolicy:
    """The current range (created with the default 5-15% the first time it's needed)."""
    policy = db.get(PayPolicy, 1)
    if policy is None:
        policy = PayPolicy(id=1, min_raise=5.0, max_raise=15.0)
        db.add(policy)
        db.commit()
    return policy


class PayPolicyIn(BaseModel):
    min_raise: float = Field(ge=0, le=100)
    max_raise: float = Field(ge=0, le=100)


@router.get("/pay-policy")
def get_pay_policy(_: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    policy = pay_policy(db)
    return {"min_raise": policy.min_raise, "max_raise": policy.max_raise}


@router.put("/pay-policy")
def set_pay_policy(body: PayPolicyIn, user: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """HR sets the range managers propose within."""
    if body.min_raise > body.max_raise:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The lowest rise can't be above the highest.")
    policy = pay_policy(db)
    policy.min_raise, policy.max_raise = body.min_raise, body.max_raise
    record(db, user, "pay_policy_changed", f"{body.min_raise:g}% to {body.max_raise:g}%")
    db.commit()
    return {"min_raise": policy.min_raise, "max_raise": policy.max_raise}


def check_raise(policy: PayPolicy, raise_percent: float, raise_reason: str | None) -> None:
    """A pay rise outside the policy's range needs a written reason of at least MIN_DISAGREEMENT_REASON characters."""
    if not policy.min_raise <= raise_percent <= policy.max_raise and (raise_reason is None or len(raise_reason) < MIN_DISAGREEMENT_REASON):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"{raise_percent:g}% is outside the pay policy ({policy.min_raise:g}% to {policy.max_raise:g}%), "
                            f"so please explain why, in at least {MIN_DISAGREEMENT_REASON} characters.")


# ─── Recommending (nominating) ────────────────────────────────────────────────
class CriterionIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    example: str = Field(min_length=10, max_length=500)


class NominationIn(BaseModel):
    employee_id: int
    proposed_title: str = Field(min_length=2, max_length=120)
    proposed_start: date
    criteria: dict[str, CriterionIn]
    reason: str = Field(min_length=10, max_length=2000)
    model_disagreement: str | None = Field(default=None, max_length=2000)
    proposed_raise: float = Field(ge=0, le=100)


@router.post("/nominations", status_code=status.HTTP_201_CREATED)
def nominate(body: NominationIn, background: BackgroundTasks, user: User = Depends(require_roles(MANAGER)),
             db: Session = Depends(get_db)):
    """A manager recommends one of their own team members for promotion."""
    employee = db.get(Employee, body.employee_id)
    if employee is None or employee.manager_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only nominate people on your own team.")
    if db.scalar(select(Nomination).where(Nomination.employee_id == employee.id, Nomination.status == "pending")):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{employee.full_name} already has a nomination waiting for HR.")
    if set(body.criteria) != set(CRITERIA):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Please rate all four: {', '.join(CRITERIA.values())}.")
    today = date.today()
    if not today <= body.proposed_start <= today + timedelta(days=366):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The start date must be between today and a year from now.")
    policy = pay_policy(db)
    if not policy.min_raise <= body.proposed_raise <= policy.max_raise:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"The pay rise must be within HR's policy: {policy.min_raise:g}% to {policy.max_raise:g}%.")

    # Recommending someone the model doesn't recommend is a disagreement, and needs a reason
    live = model()
    recommended = live.score(employee.record) >= live.threshold
    disagreement = (body.model_disagreement or "").strip() or None
    if not recommended and (disagreement is None or len(disagreement) < MIN_DISAGREEMENT_REASON):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"The model doesn't recommend {employee.full_name} yet, so please say why you disagree, "
                            f"in at least {MIN_DISAGREEMENT_REASON} characters.")

    nomination = Nomination(
        employee_id=employee.id, nominated_by=user.id, reason=body.reason.strip(),
        proposed_title=body.proposed_title.strip(), proposed_start=body.proposed_start,
        criteria_json=json.dumps({k: {"rating": c.rating, "example": c.example.strip()} for k, c in body.criteria.items()}),
        model_recommended_then=recommended, model_disagreement=disagreement if not recommended else None,
        proposed_raise=round(body.proposed_raise, 1))
    db.add(nomination)
    record(db, user, "nomination_made", f"{employee.full_name} → {nomination.proposed_title}")
    db.commit()
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.nomination_received(hr_name, employee.full_name, user.full_name,
                                                                              nomination.proposed_title))
    return {"id": nomination.id, "status": nomination.status}


def recommendation(nomination: Nomination) -> dict:
    """The manager's structured recommendation (older nominations may only have a reason)."""
    criteria = json.loads(nomination.criteria_json) if nomination.criteria_json else {}
    return {
        "proposed_title": nomination.proposed_title,
        "proposed_start": nomination.proposed_start.isoformat() if nomination.proposed_start else None,
        "criteria": [{"key": k, "label": label, **criteria[k]} for k, label in CRITERIA.items() if k in criteria],
        "reason": nomination.reason,
        "model_recommended_then": nomination.model_recommended_then,
        "model_disagreement": nomination.model_disagreement,
        "proposed_raise": nomination.proposed_raise,
    }


_NOT_GIVEN = object()


def describe(db: Session, nomination: Nomination, for_manager: bool = False, score: float | None = None,
             decision=_NOT_GIVEN, histories: dict | None = None) -> dict:
    """
    A nomination as the pages show it, with the model's current view and the decision, if any. A manager sees an
    approval only once Finance has signed off its pay rise; until then it shows as "finalising". A list passes the
    score and decision it already worked out for all its nominations at once.
    """
    employee = db.get(Employee, nomination.employee_id)
    live = model()
    if score is None:
        score = live.score(employee.record)
    if decision is _NOT_GIVEN:
        decision = db.scalar(select(Decision).where(Decision.nomination_id == nomination.id))
    result = {
        "id": nomination.id,
        "employee": {"id": employee.id, "full_name": employee.full_name, "department": employee.department},
        "nominated_by": name_of(db, nomination.nominated_by),
        "reason": nomination.reason,
        "recommendation": recommendation(nomination),
        "status": nomination.status,
        "created_at": iso(nomination.created_at),
        "model_now": {"score": round(score, 4), "threshold": live.threshold, "recommended": score >= live.threshold},
        "decision": log_entry(db, decision, histories) if decision else None,
    }
    if for_manager and decision and decision.pay_status in ("awaiting_finance", "returned"):
        result.update(status="finalising", decision=None)
    return result


@router.get("/nominations")
def list_nominations(user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """HR sees every nomination; a manager sees the ones they made. Newest first."""
    query = select(Nomination).order_by(Nomination.created_at.desc())
    if user.role == MANAGER:
        query = query.where(Nomination.nominated_by == user.id)
    nominations = list(db.scalars(query))
    scores = model().scores([db.get(Employee, n.employee_id).record for n in nominations])
    decisions = {d.nomination_id: d for d in db.scalars(select(Decision).where(
        Decision.nomination_id.in_([n.id for n in nominations])))}
    histories = pay_histories(db, [d.id for d in decisions.values()])
    return [describe(db, n, for_manager=user.role == MANAGER, score=s, decision=decisions.get(n.id), histories=histories)
            for n, s in zip(nominations, scores)]


@router.get("/nominations/{nomination_id}")
def get_nomination(nomination_id: int, user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    nomination = db.get(Nomination, nomination_id)
    if nomination is None or (user.role == MANAGER and nomination.nominated_by != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such nomination.")
    return describe(db, nomination, for_manager=user.role == MANAGER)


# ─── Deciding ─────────────────────────────────────────────────────────────────
class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=2000)
    approved_raise: float | None = Field(default=None, ge=0, le=100)
    raise_reason: str | None = Field(default=None, max_length=2000)


@router.post("/nominations/{nomination_id}/decision", status_code=status.HTTP_201_CREATED)
def decide(nomination_id: int, body: DecisionIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)),
           db: Session = Depends(get_db)):
    """HR approves (with the final pay rise) or rejects. Disagreeing with the model needs a 20-character reason."""
    nomination = db.get(Nomination, nomination_id)
    if nomination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such nomination.")
    if nomination.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This nomination has already been decided.")
    approved = body.decision == "approve"

    # What the model says right now, recorded with the decision
    live = model()
    score = live.score(db.get(Employee, nomination.employee_id).record)
    recommended = score >= live.threshold
    agrees = approved == recommended
    reason = (body.reason or "").strip() or None
    if not agrees and (reason is None or len(reason) < MIN_DISAGREEMENT_REASON):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"You are disagreeing with the model, so please give a reason of at least "
                            f"{MIN_DISAGREEMENT_REASON} characters.")

    # The pay rise: required for an approval; outside the policy range only with a written reason
    raise_percent, raise_reason = None, None
    if approved:
        if body.approved_raise is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please set the pay rise for this promotion.")
        raise_percent = round(body.approved_raise, 1)
        raise_reason = (body.raise_reason or "").strip() or None
        check_raise(pay_policy(db), raise_percent, raise_reason)

    decision = Decision(nomination_id=nomination.id, employee_id=nomination.employee_id, decided_by=user.id,
                        decision=body.decision, model_score=round(score, 4), model_threshold=live.threshold,
                        model_version=live.version,
                        model_recommended=recommended, agrees_with_model=agrees, reason=reason,
                        approved_raise=raise_percent, raise_reason=raise_reason,
                        pay_status="awaiting_finance" if approved else None)
    nomination.status = "approved" if approved else "rejected"
    db.add(decision)
    employee_name = db.get(Employee, nomination.employee_id).full_name
    record(db, user, "decision_made", f"{nomination.status}: {employee_name}{'' if agrees else ' (differs from the model)'}")
    if approved:
        db.flush()  # gives the decision its id
        db.add(PayReview(decision_id=decision.id, action="submitted", by_user=user.id, by_name=user.full_name,
                         raise_percent=raise_percent, note=raise_reason))
    db.commit()

    if approved:  # nobody is told until Finance signs off the pay rise
        for email, finance_name in finance_contacts(db):
            background.add_task(mailer.send, email, templates.pay_review_waiting(
                finance_name, employee_name, nomination.proposed_title, raise_percent))
    else:
        manager = db.get(User, nomination.nominated_by)
        if manager and manager.email:
            background.add_task(mailer.send, manager.email, templates.decision_for_manager(
                manager.full_name, employee_name, False, reason, nomination.proposed_title))
    return log_entry(db, decision)


def tell_about_promotion(background: BackgroundTasks, db: Session, decision: Decision) -> None:
    """Once Finance has signed off: email the manager, and the employee if they have an account."""
    nomination = db.get(Nomination, decision.nomination_id)
    employee_name = db.get(Employee, decision.employee_id).full_name
    manager = db.get(User, nomination.nominated_by)
    if manager and manager.email:
        background.add_task(mailer.send, manager.email, templates.decision_for_manager(
            manager.full_name, employee_name, True, decision.reason, nomination.proposed_title, decision.approved_raise))
    employee_login = login_for_employee(db, decision.employee_id)
    if employee_login and employee_login.email:
        start = nomination.proposed_start.isoformat() if nomination.proposed_start else None
        background.add_task(mailer.send, employee_login.email, templates.promotion_approved(
            employee_login.full_name, nomination.proposed_title, start, decision.approved_raise))


def pay_history(db: Session, decision_id: int) -> list[dict]:
    """Every step of the pay rise's sign-off, oldest first."""
    return pay_histories(db, [decision_id]).get(decision_id, [])


def pay_histories(db: Session, decision_ids: list[int]) -> dict[int, list[dict]]:
    """The sign-off steps of many pay rises in one query: {decision id: [step, ...]}, each oldest first."""
    found: dict[int, list[dict]] = {}
    if not decision_ids:
        return found
    steps = db.scalars(select(PayReview).where(PayReview.decision_id.in_(decision_ids)).order_by(PayReview.at, PayReview.id))
    for s in steps:
        found.setdefault(s.decision_id, []).append(
            {"action": s.action, "by": s.by_name, "at": iso(s.at), "raise": s.raise_percent, "note": s.note})
    return found


# ─── HR resubmits a pay rise Finance sent back ────────────────────────────────
class ResubmitIn(BaseModel):
    approved_raise: float = Field(ge=0, le=100)
    raise_reason: str | None = Field(default=None, max_length=2000)
    note: str = Field(min_length=10, max_length=2000)


@router.post("/decisions/{decision_id}/resubmit")
def resubmit(decision_id: int, body: ResubmitIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)),
             db: Session = Depends(get_db)):
    """HR answers Finance: a revised (or the same) pay rise, with a note. It goes back to Finance."""
    decision = db.get(Decision, decision_id)
    if decision is None or decision.decision != "approve":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such approved promotion.")
    if decision.pay_status != "returned":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a pay rise Finance has sent back can be resubmitted.")
    raise_percent = round(body.approved_raise, 1)
    raise_reason = (body.raise_reason or "").strip() or None
    check_raise(pay_policy(db), raise_percent, raise_reason)
    decision.approved_raise, decision.raise_reason, decision.pay_status = raise_percent, raise_reason, "awaiting_finance"
    db.add(PayReview(decision_id=decision.id, action="resubmitted", by_user=user.id, by_name=user.full_name,
                     raise_percent=raise_percent, note=body.note.strip()))
    employee_name = db.get(Employee, decision.employee_id).full_name
    record(db, user, "pay_resubmitted", f"{employee_name}: {raise_percent:g}%")
    db.commit()
    nomination = db.get(Nomination, decision.nomination_id)
    for email, finance_name in finance_contacts(db):
        background.add_task(mailer.send, email, templates.pay_review_waiting(
            finance_name, employee_name, nomination.proposed_title, raise_percent, resubmitted=True))
    return log_entry(db, decision)


# ─── The decision log ─────────────────────────────────────────────────────────
def log_entry(db: Session, decision: Decision, histories: dict | None = None) -> dict:
    """One decision as the log shows it. A list passes the pay histories it fetched for all its decisions at once."""
    employee = db.get(Employee, decision.employee_id)
    nomination = db.get(Nomination, decision.nomination_id)
    return {
        "id": decision.id,
        "nomination_id": decision.nomination_id,
        "employee": {"id": employee.id, "full_name": employee.full_name, "department": employee.department},
        "decision": decision.decision,
        "decided_by": name_of(db, decision.decided_by),
        "decided_at": iso(decision.decided_at),
        "model_score": decision.model_score,
        "model_threshold": decision.model_threshold,
        "model_version": decision.model_version,
        "model_recommended": decision.model_recommended,
        "agrees_with_model": decision.agrees_with_model,
        "reason": decision.reason,
        "proposed_title": nomination.proposed_title if nomination else None,
        "proposed_raise": nomination.proposed_raise if nomination else None,
        "approved_raise": decision.approved_raise,
        "raise_reason": decision.raise_reason,
        "pay_status": decision.pay_status,
        "pay_history": histories.get(decision.id, []) if histories is not None else pay_history(db, decision.id),
    }


@router.get("/decisions")
def decision_log(pay_status: str | None = None, _: User = Depends(require_roles(HR, AUDITOR)), db: Session = Depends(get_db)):
    """
    Every decision, newest first. HR, and the compliance auditor (read-only). `pay_status` keeps only those at one
    step of Finance's sign-off (the notification bell asks only for the ones Finance sent back).
    """
    query = select(Decision).order_by(Decision.decided_at.desc(), Decision.id.desc())
    if pay_status:
        query = query.where(Decision.pay_status == pay_status)
    decisions = list(db.scalars(query))
    histories = pay_histories(db, [d.id for d in decisions])
    return [log_entry(db, d, histories) for d in decisions]


# ─── The employee's own promotions ────────────────────────────────────────────
@router.get("/my-promotions")
def my_promotions(user: User = Depends(require_roles(EMPLOYEE)), db: Session = Depends(get_db)):
    """
    An employee's approved promotions: new role, start date and pay rise. Pending nominations aren't shown, and
    nor are approvals whose pay rise Finance hasn't signed off yet.
    """
    if not user.employee_id:
        return []
    rows = []
    signed_off = (Decision.pay_status.is_(None)) | (Decision.pay_status == "signed_off")  # empty: before Finance existed
    for decision in db.scalars(select(Decision).where(Decision.employee_id == user.employee_id, Decision.decision == "approve", signed_off)
                               .order_by(Decision.decided_at.desc())):
        nomination = db.get(Nomination, decision.nomination_id)
        rows.append({"title": nomination.proposed_title, "approved_on": decision.decided_at.date().isoformat(),
                     "start": nomination.proposed_start.isoformat() if nomination.proposed_start else None,
                     "raise": decision.approved_raise})
    return rows
