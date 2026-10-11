"""
The feedback channel's tables: how employees respond to their explanation.

- ExplanationRating: an employee rates their explanation (clear? useful?) and may mark factors as "seems wrong" or
  "seems unfair". Seen by HR and the auditor only in aggregate, never by managers. Ratings never reach the model.
- CorrectionRequest: an employee asks HR to correct a value in their work record, with evidence. Only when HR
  confirms it is the record changed (and the employee re-scored, logged in promotion.RecordChange).
- NominationDeferral: HR puts a promotion decision on hold until a pending correction is resolved. Not a decision,
  so never counted as agreeing or disagreeing with the model.

The promotion code never reads these tables (tests/test_isolation.py checks this).
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ExplanationRating(Base):
    """One employee's rating of the explanation from one model version (rating again replaces it)."""
    __tablename__ = "explanation_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    model_version: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)                  # the readiness score the explanation was about
    clarity: Mapped[int] = mapped_column(Integer)                # 1-5: "This explanation was clear"
    usefulness: Mapped[int] = mapped_column(Integer)             # 1-5: "This explanation was useful"
    flagged_json: Mapped[str] = mapped_column(Text, default="[]")  # [{"feature": ..., "kind": "wrong" | "unfair"}]
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class CorrectionRequest(Base):
    """A request to correct one value in an employee's work record, and HR's decision on it."""
    __tablename__ = "correction_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    # Who started it. Always "employee" in this version (an earlier version also had HR-opened re-appraisals)
    source: Mapped[str] = mapped_column(String(20), default="employee")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    field: Mapped[str] = mapped_column(String(40))               # a record field (app.promotion.records.ENTRY_FIELDS)
    current_value: Mapped[float] = mapped_column(Float)          # in the units HR types in (e.g. 93 for 93%)
    requested_value: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text)                      # the evidence, in words
    evidence_name: Mapped[str | None] = mapped_column(String(80), nullable=True)  # a stored file (random name)
    evidence_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending, confirmed or rejected
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    record_change_id: Mapped[int | None] = mapped_column(ForeignKey("record_changes.id"), nullable=True)
    score_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    employee_seen: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)  # outcome seen


class NominationDeferral(Base):
    """A promotion decision put on hold while a record correction is pending."""
    __tablename__ = "nomination_deferrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nomination_id: Mapped[int] = mapped_column(ForeignKey("nominations.id"), index=True)
    deferred_by_name: Mapped[str] = mapped_column(String(120))
    deferred_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lifted_because: Mapped[str | None] = mapped_column(String(40), nullable=True)  # resolved or resumed by HR
