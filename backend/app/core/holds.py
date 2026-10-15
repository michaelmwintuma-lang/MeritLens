"""
Decision holds: "don't decide this promotion yet".

HR puts a nomination on hold while a record correction for the nominee is pending, because the correction may
change their score. The feedback code places and lifts holds; the decision code reads them and refuses a decision
while one is active.

This table is deliberately neutral: it says only that a nomination is held, why (a fixed code), by whom and when.
It never holds the correction itself, the employee's words or any rating, so the promotion code can read it
without ever seeing feedback (tests/test_isolation.py).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base

REASONS = {"correction_pending": "a record correction for the nominee is pending"}


def now() -> datetime:
    return datetime.now(timezone.utc)


class DecisionHold(Base):
    __tablename__ = "decision_holds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nomination_id: Mapped[int] = mapped_column(ForeignKey("nominations.id"), index=True)
    reason: Mapped[str] = mapped_column(String(40), default="correction_pending")  # a key of REASONS
    placed_by_name: Mapped[str] = mapped_column(String(120))
    placed_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lifted_because: Mapped[str | None] = mapped_column(String(40), nullable=True)  # resolved or resumed by HR


def active_hold(db: Session, nomination_id: int) -> DecisionHold | None:
    return db.scalar(select(DecisionHold).where(DecisionHold.nomination_id == nomination_id,
                                                DecisionHold.lifted_at.is_(None)))


def place_hold(db: Session, nomination_id: int, by_name: str, reason: str = "correction_pending") -> DecisionHold:
    """Put a nomination on hold (does nothing if it already is). The caller commits."""
    assert reason in REASONS, reason
    hold = active_hold(db, nomination_id)
    if hold is None:
        hold = DecisionHold(nomination_id=nomination_id, reason=reason, placed_by_name=by_name)
        db.add(hold)
    return hold


def lift_hold(db: Session, nomination_id: int, because: str) -> DecisionHold | None:
    """Lift the active hold, if any. The caller commits."""
    hold = active_hold(db, nomination_id)
    if hold is not None:
        hold.lifted_at, hold.lifted_because = now(), because
    return hold
