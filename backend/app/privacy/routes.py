"""
People's rights over their data (UK/EU GDPR articles 15, 17 and 22; Ghana's Data Protection Act 2012 has the same
ideas), built in:

- **A copy of my data** (everyone signed in): one JSON file with everything the platform holds about you: your
  account, your employee record, your saved scores in each review cycle, your explanation ratings and correction
  requests, the promotion decisions about you, your record's history, your equality-monitoring answers (kept apart
  and used only for the fairness check), your notifications and your activity-log entries.
- **Erasing someone who has left** (HR): their name, work record, ratings, correction requests (and evidence
  files), equality-monitoring answers and saved inputs are removed. What must stay for accountability stays, under a
  pseudonym ("Former employee no. 123"): the promotion decisions and nominations, scores in closed review cycles, and
  the tamper-evident audit trail (which by design can't be changed). They leave every list, score and check.
- **Retention** (retention.py): old rating comments, notifications, email-log entries and activity-log entries are
  removed after set periods, every day.

The model only advises and people decide (article 22): every score comes with its explanation, a way to rate it and
to ask for a correction, and every decision is a person's.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import audit
from app.core.activity import ActivityEntry, record
from app.core.config import RETENTION_DAYS
from app.core.database import get_db
from app.core.mailer import EmailLog
from app.core.notifications import Notification
from app.core.roles import HR
from app.core.security import get_current_user, require_roles
from app.feedback import corrections
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.governance.models import EqualityMonitoring
from app.promotion.models import CycleScore, Decision, Employee, Nomination, RecordChange, ReviewCycle

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/retention")
def retention_periods():
    """How long each kind of personal data is kept (public: shown on the privacy page)."""
    return RETENTION_DAYS


def plain(value):
    """A value as JSON shows it: dates and times as text."""
    return value.isoformat() if hasattr(value, "isoformat") else value


def rows(objects, *skip) -> list[dict]:
    """Table rows as plain dictionaries: every column except the ones named in `skip`."""
    return [{c.name: plain(getattr(o, c.name)) for c in o.__table__.columns if c.name not in skip} for o in objects]


@router.get("/my-data")
def my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything the platform holds about you, as one JSON file (to keep, or to ask questions about)."""
    data = {
        "about": "Everything MeritLens holds about you, on the day you downloaded it. Scores are readiness scores: "
                 "the model only advises, and people make every decision.",
        "downloaded_at": plain(datetime.now(timezone.utc)),
        "account": rows([user], "password_hash", "token_version", "failed_logins", "locked_until", "photo")[0],
        "notifications": rows(db.scalars(select(Notification).where(Notification.user_id == user.id))),
        "activity_log": rows(db.scalars(select(ActivityEntry).where(ActivityEntry.user_id == user.id))),
        "emails_sent_to_you": rows(db.scalars(select(EmailLog).where(EmailLog.to_address == (user.email or ""))), "mail_json"),
    }
    employee = db.get(Employee, user.employee_id) if user.employee_id else None
    if employee is not None:
        cycles = {c.id: c.name for c in db.scalars(select(ReviewCycle))}
        data["employee_record"] = {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
                                   "manager_user_id": employee.manager_user_id, "inputs": json.loads(employee.record_json)}
        data["scores_in_review_cycles"] = [{**r, "cycle": cycles.get(r["cycle_id"])} for r in rows(
            db.scalars(select(CycleScore).where(CycleScore.employee_id == employee.id)))]
        data["record_history"] = rows(db.scalars(select(RecordChange).where(RecordChange.employee_id == employee.id)))
        data["explanation_ratings"] = rows(db.scalars(select(ExplanationRating).where(ExplanationRating.employee_id == employee.id)))
        data["correction_requests"] = rows(db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == employee.id)), "evidence_name")
        data["nominations_about_you"] = rows(db.scalars(select(Nomination).where(Nomination.employee_id == employee.id)))
        data["decisions_about_you"] = rows(db.scalars(select(Decision).where(Decision.employee_id == employee.id)))
        data["equality_monitoring"] = rows(db.scalars(select(EqualityMonitoring).where(EqualityMonitoring.employee_id == employee.id)))
    record(db, user, "data_downloaded", "")
    db.commit()
    name = f"meritlens-my-data-{datetime.now(timezone.utc).date().isoformat()}.json"
    return Response(json.dumps(data, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


class EraseIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)  # e.g. "Left the organisation on 30 June 2026"


@router.post("/employees/{employee_id}/erase")
def erase(employee_id: int, body: EraseIn, user: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """HR erases someone who has left (see this module's notes for what is removed and what stays, pseudonymised)."""
    employee = db.get(Employee, employee_id)
    if employee is None or employee.left_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    if db.scalar(select(Nomination).where(Nomination.employee_id == employee.id, Nomination.status == "pending")):
        raise HTTPException(status.HTTP_409_CONFLICT, "A nomination for them is still waiting for a decision. Decide it first.")
    if db.scalar(select(Decision).where(Decision.employee_id == employee.id, Decision.pay_status.in_(("awaiting_finance", "returned")))):
        raise HTTPException(status.HTTP_409_CONFLICT, "Finance hasn't signed off their pay rise yet. Finish that first.")

    # Their feedback: ratings, correction requests and the evidence files
    for request in db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == employee.id)):
        path = corrections.evidence_path(request)
        if path is not None:
            path.unlink(missing_ok=True)
    db.execute(delete(CorrectionRequest).where(CorrectionRequest.employee_id == employee.id))
    db.execute(delete(ExplanationRating).where(ExplanationRating.employee_id == employee.id))
    db.execute(delete(EqualityMonitoring).where(EqualityMonitoring.employee_id == employee.id))
    # Saved inputs: scores stay (closed cycles' totals mustn't change), the inputs they came from don't
    db.execute(update(CycleScore).where(CycleScore.employee_id == employee.id).values(record_json="{}"))
    db.execute(update(RecordChange).where(RecordChange.employee_id == employee.id).values(changes_json="[]", reason=None))
    db.execute(update(User).where(User.employee_id == employee.id).values(employee_id=None))
    employee.full_name = f"Former employee no. {employee.id}"
    employee.record_json, employee.manager_user_id = "{}", None
    employee.left_at = datetime.now(timezone.utc)
    audit.append(db, "employee_erased", user, "employee", employee.id, {"reason": body.reason.strip()})
    record(db, user, "employee_erased", f"no. {employee.id}")
    db.commit()
    return {"erased": employee.id, "pseudonym": employee.full_name}
