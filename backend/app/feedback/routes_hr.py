"""
HR's side of the feedback channel.

- The correction queue: each request with the value, the requested value and the evidence. HR confirms it (entering
  the value they verified) or rejects it (with a reason the employee receives). Confirming updates the record,
  re-scores the employee and logs it in the record's history (who, old and new value, reason, readiness before and
  after, model version); the employee is told either way.
- The committee note: while a correction is pending for someone with a nomination, HR's review page says so, and
  HR may put the decision on hold until it is resolved. A hold is not a decision.
- The ratings summary for HR and the auditor: aggregates only, never one person's rating.
"""
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import login_for_employee
from app.accounts.models import User
from app.core import approvals, audit
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_db
from app.core.holds import active_hold, lift_hold, place_hold
from app.core.roles import AUDITOR, HR
from app.core.security import require_roles
from app.feedback import corrections
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.feedback.routes import evidence_file
from app.promotion.features import MODEL_FEATURES
from app.promotion.labels import label
from app.promotion.models import Employee, Nomination
from app.promotion.routes import model
from app.promotion.routes_records import record_history

router = APIRouter(prefix="/api/hr/feedback", tags=["feedback (HR)"])
hr_only = require_roles(HR)
MIN_REASON = 20
MIN_GROUP = 5  # rates are shown only for at least this many ratings, so no one person's answer can be read off


def get_request(db: Session, request_id: int) -> CorrectionRequest:
    request = db.get(CorrectionRequest, request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such request.")
    return request


def name_of(db: Session, employee_id: int) -> str:
    employee = db.get(Employee, employee_id)
    return employee.full_name if employee else "unknown"


# ─── The correction queue ─────────────────────────────────────────────────────
@router.get("/corrections")
def queue(status_filter: str | None = None, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """Every correction request: waiting ones first (oldest first), then decided ones (newest first)."""
    query = select(CorrectionRequest)
    if status_filter:
        query = query.where(CorrectionRequest.status == status_filter)
    rows = list(db.scalars(query))
    rows.sort(key=lambda r: (r.status != "pending", r.created_at if r.status == "pending" else -r.decided_at.timestamp()))
    names = {e.id: e.full_name for e in db.scalars(select(Employee).where(Employee.id.in_({r.employee_id for r in rows})))}
    return [corrections.describe(r, names.get(r.employee_id)) for r in rows]


@router.get("/corrections/{request_id}")
def one_request(request_id: int, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    request = get_request(db, request_id)
    return corrections.describe(request, name_of(db, request.employee_id))


@router.get("/corrections/{request_id}/evidence")
def request_evidence(request_id: int, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    return evidence_file(get_request(db, request_id))


def pending_request(db: Session, request_id: int) -> CorrectionRequest:
    request = get_request(db, request_id)
    if request.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This request has already been decided.")
    return request


def tell_employee(background: BackgroundTasks, db: Session, request: CorrectionRequest) -> None:
    login = login_for_employee(db, request.employee_id)
    if login and login.email:
        background.add_task(mailer.send, login.email, templates.correction_decided(
            login.full_name, corrections.field_label(request.field), request.status == "confirmed",
            corrections.show(request.field, request.verified_value), request.decision_reason))


class ConfirmIn(BaseModel):
    verified_value: float
    note: str | None = Field(default=None, max_length=2000)


@router.post("/corrections/{request_id}/confirm")
def confirm(request_id: int, body: ConfirmIn, background: BackgroundTasks, db: Session = Depends(get_db),
            user: User = Depends(hr_only)):
    """
    HR checked the evidence and confirms the value they verified (which may differ from the one asked for). The
    record is corrected, the employee re-scored, and both scores logged with the model version.
    """
    request = pending_request(db, request_id)
    value = corrections.check_value(request.field, body.verified_value)
    employee = db.get(Employee, request.employee_id)
    if value == corrections.current_value(employee, request.field):
        raise corrections.unprocessable("That is the value already in the record. If it is right, reject the request instead.")
    note = (body.note or "").strip() or None
    if approvals.on():
        old, new = corrections.corrected_record(employee, request.field, value)
        live = model()
        before, after = live.score(old) >= live.threshold, live.score(new) >= live.threshold
        if before != after:  # it changes whether the model recommends them: a second HR person approves it
            moves = "above" if after else "below"
            entry = approvals.request(
                db, background, "correction_confirm", request.id,
                f"Correct {employee.full_name}'s {corrections.field_label(request.field)} to "
                f"{corrections.show(request.field, value)}, which moves them {moves} the threshold",
                {"verified_value": value, "note": note}, user)
            db.commit()
            return approvals.pending_response(entry)
    return confirm_now(db, background, request, employee, value, note, user)


def confirm_now(db: Session, background: BackgroundTasks, request: CorrectionRequest, employee: Employee, value: float,
                note: str | None, user: User):
    """Correct the record, re-score the employee, and tell them. The caller has checked the value."""
    old, new = corrections.corrected_record(employee, request.field, value)
    employee.record_json = json.dumps(new)
    change = record_history(db, employee, old, new, user, "correction",
                            f"Correction request {request.id} confirmed" + (f": {note}" if note else ""))
    db.flush()
    request.status, request.verified_value, request.decision_reason = "confirmed", value, note
    request.decided_by, request.decided_by_name = user.id, user.full_name
    request.decided_at = datetime.now(timezone.utc)
    request.record_change_id, request.score_before, request.score_after = change.id, change.score_before, change.score_after
    request.employee_seen = False
    db.flush()  # the session doesn't flush by itself, and the check below must see this request as decided
    audit.append(db, "correction_confirmed", user, "correction", request.id,
                 {"employee_id": employee.id, "field": request.field, "requested": request.requested_value,
                  "verified": value, "score_before": change.score_before, "score_after": change.score_after,
                  "record_change_id": change.id}, model_version=change.model_version)
    corrections.lift_holds_if_resolved(db, employee.id, user)
    record(db, user, "correction_confirmed", f"{employee.full_name}: {corrections.field_label(request.field)}")
    db.commit()
    tell_employee(background, db, request)
    return corrections.describe(request, employee.full_name)


def approved_correction(db, entry, payload, requester, approver, background):
    """A second HR person approved the correction: it is made now, in the name of the person who checked it."""
    request = pending_request(db, int(entry.subject))
    employee = db.get(Employee, request.employee_id)
    note = f"{payload['note'] or 'Confirmed'} (approved by {approver.full_name})"
    return confirm_now(db, background, request, employee, payload["verified_value"], note, requester)


approvals.register("correction_confirm", approved_correction)


class RejectIn(BaseModel):
    reason: str = Field(max_length=2000)


@router.post("/corrections/{request_id}/reject")
def reject(request_id: int, body: RejectIn, background: BackgroundTasks, db: Session = Depends(get_db),
           user: User = Depends(hr_only)):
    """HR keeps the record as it is, with a reason (at least 20 characters) that the employee receives."""
    request = pending_request(db, request_id)
    reason = body.reason.strip()
    if len(reason) < MIN_REASON:
        raise corrections.unprocessable(f"Please explain why, in at least {MIN_REASON} characters. The employee receives it.")
    request.status, request.decision_reason = "rejected", reason
    approvals.withdraw(db, "correction_confirm", request.id, user, "The correction request was rejected instead.")
    request.decided_by, request.decided_by_name = user.id, user.full_name
    request.decided_at = datetime.now(timezone.utc)
    request.employee_seen = False
    db.flush()  # the session doesn't flush by itself, and the check below must see this request as decided
    audit.append(db, "correction_rejected", user, "correction", request.id,
                 {"employee_id": request.employee_id, "field": request.field, "requested": request.requested_value})
    corrections.lift_holds_if_resolved(db, request.employee_id, user)
    employee_name = name_of(db, request.employee_id)
    record(db, user, "correction_rejected", f"{employee_name}: {corrections.field_label(request.field)}")
    db.commit()
    tell_employee(background, db, request)
    return corrections.describe(request, employee_name)


# ─── The committee note, and putting a decision on hold ───────────────────────
def get_nomination(db: Session, nomination_id: int) -> Nomination:
    nomination = db.get(Nomination, nomination_id)
    if nomination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such nomination.")
    return nomination


@router.get("/nominations/{nomination_id}/note")
def committee_note(nomination_id: int, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """
    Pending corrections to the nominee's record (the score may change), and whether the decision is on hold. While
    it is, the decision API refuses a decision (app/promotion/routes_decisions.py).
    """
    nomination = get_nomination(db, nomination_id)
    pending = corrections.pending_for(db, nomination.employee_id)
    hold = active_hold(db, nomination.id)
    return {"pending_corrections": [corrections.describe(r) for r in pending],
            "deferred": bool(hold),
            "deferred_by": hold.placed_by_name if hold else None,
            "deferred_at": hold.placed_at.isoformat(timespec="seconds") if hold else None}


@router.post("/nominations/{nomination_id}/defer")
def defer(nomination_id: int, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """Hold the decision until the nominee's pending corrections are resolved. Not a decision, and not an override."""
    nomination = get_nomination(db, nomination_id)
    if nomination.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This nomination has already been decided.")
    if not corrections.pending_for(db, nomination.employee_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "No correction is pending for this person, so there is nothing to wait for.")
    if active_hold(db, nomination.id) is None:
        place_hold(db, nomination.id, user.full_name)
        audit.append(db, "hold_placed", user, "nomination", nomination.id, {"reason": "correction_pending"})
        record(db, user, "nomination_deferred", name_of(db, nomination.employee_id))
        db.commit()
    return committee_note(nomination.id, db)


@router.post("/nominations/{nomination_id}/resume")
def resume(nomination_id: int, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """Take the decision off hold without waiting for the correction."""
    nomination = get_nomination(db, nomination_id)
    if lift_hold(db, nomination.id, "resumed") is not None:
        audit.append(db, "hold_lifted", user, "nomination", nomination.id, {"because": "resumed"})
        record(db, user, "nomination_resumed", name_of(db, nomination.employee_id))
        db.commit()
    return committee_note(nomination.id, db)


# ─── Ratings, in aggregate ────────────────────────────────────────────────────
ratings_router = APIRouter(prefix="/api/feedback/ratings", tags=["feedback (HR)"])


@ratings_router.get("/summary")
def ratings_summary(db: Session = Depends(get_db), _: User = Depends(require_roles(HR, AUDITOR))):
    """
    How employees rated their explanations, in aggregate only: the share rating clarity and usefulness 4 or 5 (shown
    only from MIN_GROUP ratings), and how often each factor was marked wrong or unfair. Never one person's rating.
    """
    ratings = list(db.scalars(select(ExplanationRating)))
    count = len(ratings)
    marks = Counter()
    for r in ratings:
        for flag in json.loads(r.flagged_json):
            marks[(flag["feature"], flag["kind"])] += 1
    rate = (lambda key: round(sum(getattr(r, key) >= 4 for r in ratings) / count, 4)) if count >= MIN_GROUP else (lambda key: None)
    contested = [{"feature": f, "label": label(f), "wrong": marks[(f, "wrong")], "unfair": marks[(f, "unfair")],
                  "share": round((marks[(f, "wrong")] + marks[(f, "unfair")]) / count, 4) if count >= MIN_GROUP else None}
                 for f in MODEL_FEATURES if marks[(f, "wrong")] or marks[(f, "unfair")]]
    return {"ratings": count, "min_group": MIN_GROUP, "clarity_rate": rate("clarity"), "usefulness_rate": rate("usefulness"),
            "contested": sorted(contested, key=lambda c: -(c["wrong"] + c["unfair"]))}
