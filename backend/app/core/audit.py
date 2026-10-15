"""
The audit trail: an append-only, tamper-evident record of every event that matters for accountability.

Each event says what happened (a nomination, a decision, a pay step, a record change, a correction, a hold, a model
release), who did it, about what, which model version was live, and what the model said at that moment. With it,
an auditor can rebuild exactly what the model said and what each person did, at any point in time.

Tamper-evident: every event stores a SHA-256 hash of its own content together with the previous event's hash (a
hash chain). Changing or deleting any past event breaks every hash after it, and verify() finds where. The code
never updates or deletes an event (enforced below); with PostgreSQL, the database roles can't either
(deploy/postgres/setup.sql).

Unlike the activity log (dates only, for privacy), events keep the exact time: they record decisions about
promotions, which already carry their time, not people's working habits. Free text that employees write
(correction notes, rating comments) is never copied in.
"""
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, event, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base

GENESIS = "0" * 64

# The events, in the words the auditor sees
EVENTS = {
    "nomination_made": "Manager recommended an employee for promotion",
    "decision_made": "HR decided on a nomination",
    "pay_submitted": "Pay rise sent to Finance",
    "pay_returned": "Finance sent a pay rise back to HR",
    "pay_resubmitted": "HR resubmitted a pay rise",
    "pay_signed_off": "Finance signed off a pay rise",
    "record_changed": "An employee's work record changed",
    "correction_requested": "Employee asked for a record correction",
    "correction_confirmed": "HR confirmed a record correction",
    "correction_rejected": "HR rejected a record correction",
    "hold_placed": "A decision was put on hold",
    "hold_lifted": "A decision hold was lifted",
    "model_registered": "A newly trained model was registered",
    "model_released": "A model version was released (made live)",
    "cycle_opened": "HR opened a review cycle (everyone scored and saved)",
    "cycle_closed": "HR closed a review cycle",
    "team_changed": "An employee's manager changed",
    "cover_arranged": "Cover arranged while a manager is away",
    "cover_ended": "Cover ended early",
    "payroll_sent": "Finance handed signed-off pay rises to payroll",
}


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime)
    event: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120))        # kept even if the account is renamed or deleted
    subject_type: Mapped[str] = mapped_column(String(20))       # employee, nomination, decision, correction, model, cycle or cover
    subject_id: Mapped[str] = mapped_column(String(60), index=True)
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


@event.listens_for(AuditEvent, "before_update")
@event.listens_for(AuditEvent, "before_delete")
def _append_only(*_):
    raise PermissionError("Audit events can't be changed or deleted.")


def _digest(prev_hash: str, at: datetime, event_name: str, actor_id, actor_name: str, subject_type: str,
            subject_id: str, model_version, payload_json: str) -> str:
    """The event's hash: its content and the previous event's hash, in a fixed (canonical) order."""
    content = json.dumps([prev_hash, at.isoformat(timespec="microseconds"), event_name, actor_id, actor_name,
                          subject_type, subject_id, model_version, payload_json], separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def _last_hash(db: Session) -> str:
    if db.get_bind().dialect.name == "postgresql":
        # Two requests appending at once would both link to the same previous event; one waits for the other
        db.execute(text("SELECT pg_advisory_xact_lock(7426)"))
    last = db.scalar(select(AuditEvent.hash).order_by(AuditEvent.id.desc()).limit(1))
    return last or GENESIS


def append(db: Session, event_name: str, actor, subject_type: str, subject_id, payload: dict | None = None,
           model_version: str | None = None) -> AuditEvent:
    """
    Add an event to the chain. `actor` is a User (or None for the system). The caller commits it together with the
    change it describes, so an event exists exactly when the change does.
    """
    assert event_name in EVENTS, event_name
    at = datetime.now(timezone.utc).replace(tzinfo=None)
    payload_json = json.dumps(payload or {}, sort_keys=True, default=str)
    actor_id, actor_name = (actor.id, actor.full_name) if actor is not None else (None, "system")
    prev = _last_hash(db)
    entry = AuditEvent(at=at, event=event_name, actor_id=actor_id, actor_name=actor_name, subject_type=subject_type,
                       subject_id=str(subject_id), model_version=model_version, payload_json=payload_json,
                       prev_hash=prev, hash=_digest(prev, at, event_name, actor_id, actor_name, subject_type,
                                                    str(subject_id), model_version, payload_json))
    db.add(entry)
    db.flush()  # the next event in this same request must link to this one
    return entry


def verify(db: Session) -> dict:
    """Recompute the whole chain. Intact: every hash matches its content and links to the event before it."""
    prev, count = GENESIS, 0
    for e in db.scalars(select(AuditEvent).order_by(AuditEvent.id)):
        expected = _digest(e.prev_hash, e.at, e.event, e.actor_id, e.actor_name, e.subject_type, e.subject_id,
                           e.model_version, e.payload_json)
        if e.prev_hash != prev or e.hash != expected:
            return {"intact": False, "events": count, "first_broken_id": e.id,
                    "problem": "links to the wrong previous event" if e.prev_hash != prev else "content was changed"}
        prev, count = e.hash, count + 1
    return {"intact": True, "events": count, "first_broken_id": None, "problem": None}


def describe(e: AuditEvent) -> dict:
    return {"id": e.id, "at": e.at.isoformat(timespec="seconds"), "event": e.event, "label": EVENTS.get(e.event, e.event),
            "actor": e.actor_name, "subject_type": e.subject_type, "subject_id": e.subject_id,
            "model_version": e.model_version, "payload": json.loads(e.payload_json), "hash": e.hash}
