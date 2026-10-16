"""
A second person for the riskiest actions (the "four-eyes" rule), switched on with FOUR_EYES=1:

- releasing a model version (it changes every score), and
- confirming a record correction that moves someone across the threshold (it changes whether the model recommends
  them).

With the rule on, the HR person's action becomes a request; a different HR person approves it (which carries it out)
or declines it. Both names are kept, with the time, in the request and in the audit trail. With the rule off (the
default, and with one HR account it must be), actions happen at once as before.

Each kind of action registers what "carry it out" means (register()), so this module knows nothing about models or
records.
"""
import json
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.accounts.contacts import hr_contacts
from app.accounts.models import User
from app.core import audit
from app.core import email_templates as templates
from app.core import mailer
from app.core.database import Base, get_db
from app.core.roles import HR
from app.core.security import require_roles

KINDS = {"model_release": "Release a model version", "correction_confirm": "Confirm a record correction that crosses the threshold"}
_handlers: dict[str, Callable] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))                 # a key of KINDS
    subject: Mapped[str] = mapped_column(String(60))              # the model version, or the correction request's id
    summary: Mapped[str] = mapped_column(String(300))             # what is asked, in words
    payload_json: Mapped[str] = mapped_column(Text, default="{}")  # what the action needs (e.g. the verified value)
    requested_by: Mapped[int] = mapped_column(Integer)
    requested_by_name: Mapped[str] = mapped_column(String(120))
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending, approved or declined
    decided_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


def on() -> bool:
    from app.core import config
    return config.FOUR_EYES


def register(kind: str, carry_out: Callable) -> None:
    """carry_out(db, approval, payload, requester, approver, background) does the action; it may raise HTTPException."""
    _handlers[kind] = carry_out


def request(db: Session, background: BackgroundTasks, kind: str, subject, summary: str, payload: dict, user: User) -> Approval:
    """Ask a second HR person to approve this action. One open request per action. The caller commits."""
    existing = db.scalar(select(Approval).where(Approval.kind == kind, Approval.subject == str(subject), Approval.status == "pending"))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This is already waiting for a second HR person's approval (asked by {existing.requested_by_name}).")
    entry = Approval(kind=kind, subject=str(subject), summary=summary[:300], payload_json=json.dumps(payload),
                     requested_by=user.id, requested_by_name=user.full_name)
    db.add(entry)
    db.flush()
    audit.append(db, "approval_requested", user, "approval", entry.id, {"kind": kind, "subject": str(subject)})
    for email, name in hr_contacts(db):
        if email != user.email:
            background.add_task(mailer.send, email, templates.approval_needed(name, user.full_name, summary))
    return entry


def withdraw(db: Session, kind: str, subject, user: User, reason: str) -> None:
    """Close a waiting request whose subject was decided another way (e.g. the correction was rejected)."""
    entry = db.scalar(select(Approval).where(Approval.kind == kind, Approval.subject == str(subject), Approval.status == "pending"))
    if entry is not None:
        entry.status, entry.decided_by_name, entry.decided_at, entry.decision_note = "declined", user.full_name, now(), reason


def describe(a: Approval) -> dict:
    return {"id": a.id, "kind": a.kind, "kind_label": KINDS[a.kind], "subject": a.subject, "summary": a.summary,
            "requested_by": a.requested_by_name, "requested_by_id": a.requested_by,
            "requested_at": a.requested_at.isoformat(timespec="seconds"), "status": a.status,
            "decided_by": a.decided_by_name, "decided_at": a.decided_at.isoformat(timespec="seconds") if a.decided_at else None,
            "decision_note": a.decision_note}


def pending_response(entry: Approval):
    """The answer to an action that is now waiting for a second person (HTTP 202)."""
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"approval": describe(entry)})


router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
def list_approvals(status_filter: str | None = "pending", _: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """Requests waiting for a second HR person (or all of them), newest first, and whether the rule is on."""
    query = select(Approval).order_by(Approval.requested_at.desc(), Approval.id.desc())
    if status_filter:
        query = query.where(Approval.status == status_filter)
    return {"four_eyes": on(), "items": [describe(a) for a in db.scalars(query.limit(100))]}


def open_approval(db: Session, approval_id: int, user: User) -> Approval:
    entry = db.get(Approval, approval_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such request.")
    if entry.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This request has already been decided.")
    if entry.requested_by == user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A second HR person must approve this: you asked for it.")
    return entry


class DecideIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@router.post("/{approval_id}/approve")
def approve(approval_id: int, body: DecideIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)),
            db: Session = Depends(get_db)):
    """A second HR person approves: the action is carried out now, in both people's names."""
    entry = open_approval(db, approval_id, user)
    requester = db.get(User, entry.requested_by)
    result = _handlers[entry.kind](db, entry, json.loads(entry.payload_json), requester, user, background)
    entry.status, entry.decided_by_name, entry.decided_at = "approved", user.full_name, now()
    entry.decision_note = (body.note or "").strip() or None
    audit.append(db, "approval_given", user, "approval", entry.id, {"kind": entry.kind, "subject": entry.subject})
    db.commit()
    return {"approval": describe(entry), "result": result}


@router.post("/{approval_id}/decline")
def decline(approval_id: int, body: DecideIn, user: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """A second HR person declines: nothing changes, and the request is closed with their note."""
    entry = open_approval(db, approval_id, user)
    if not (body.note or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please say why, for the person who asked.")
    entry.status, entry.decided_by_name, entry.decided_at, entry.decision_note = "declined", user.full_name, now(), body.note.strip()
    audit.append(db, "approval_declined", user, "approval", entry.id, {"kind": entry.kind, "subject": entry.subject})
    db.commit()
    return {"approval": describe(entry)}
