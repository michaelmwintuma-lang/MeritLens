"""The promotion part's tables: the employee directory, cover between managers, review cycles, nominations, and decisions."""
import json
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Employee(Base):
    """
    One employee: name, department, manager, and their work record (the model's inputs).
    Protected characteristics (gender, age, education...) and pay are deliberately not stored here at all.
    """
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(60))
    # The manager's user account; a manager sees only employees whose manager_user_id is theirs
    manager_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # The model's inputs, stored as JSON text: {"performance_score": 81.2, ...}
    record_json: Mapped[str] = mapped_column(Text)
    # Set when someone who has left is erased (app/privacy): their name and record are removed and they leave every
    # list, score and check; past decisions about them stay in the log under this pseudonymous row
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def record(self) -> dict:
        """The work record as a dictionary, including department."""
        return {**json.loads(self.record_json), "department": self.department}


def current_employees():
    """A query for everyone in the directory now (not people who have left and been erased)."""
    return select(Employee).where(Employee.left_at.is_(None))


class TeamCover(Base):
    """
    A manager away for a while hands their team to another manager, who may then see and nominate them, from the
    first day to the last (both included). Set by the manager or by HR; it ends by itself, or earlier if ended.
    """
    __tablename__ = "team_covers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)   # the manager who is away
    cover_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)     # the manager covering
    starts: Mapped[date] = mapped_column(Date)
    ends: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    set_by_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)        # ended early


class ReviewCycle(Base):
    """
    A review cycle (e.g. "2026 mid-year"): HR opens it, the live model scores every employee once and the scores are
    saved (CycleScore), managers nominate until the nomination deadline, HR decides, and HR closes it. Everyone in a
    cycle is scored by the same model: a new model can't be released while a cycle is open.
    """
    __tablename__ = "review_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(10), default="open")        # open or closed; at most one is open
    model_version: Mapped[str] = mapped_column(String(40))
    threshold: Mapped[float] = mapped_column(Float)
    nominations_close: Mapped[date | None] = mapped_column(Date, nullable=True)  # the last day managers may nominate
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by_name: Mapped[str] = mapped_column(String(120))               # kept even if the account is renamed or deleted
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CycleScore(Base):
    """
    One employee's saved score in a review cycle, with the exact inputs it was worked out from, so it can always be
    reproduced. It changes only when the employee's record changes during the open cycle (HR edits it or confirms a
    correction); the score at opening is kept, and the record change that moved it is linked.
    """
    __tablename__ = "cycle_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    recommended: Mapped[bool] = mapped_column(Boolean)
    record_json: Mapped[str] = mapped_column(Text)                          # the inputs the score was worked out from
    score_at_opening: Mapped[float | None] = mapped_column(Float, nullable=True)  # empty: added after the cycle opened
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    record_change_id: Mapped[int | None] = mapped_column(ForeignKey("record_changes.id"), nullable=True)


class Nomination(Base):
    """A manager proposes a team member for promotion, with a short reason. HR decides."""
    __tablename__ = "nominations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    nominated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved or rejected
    # The manager's structured recommendation (all optional in the table, so older nominations still load)
    proposed_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proposed_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    criteria_json: Mapped[str | None] = mapped_column(Text, nullable=True)     # {"performance": {"rating": 4, "example": "..."}, ...}
    model_recommended_then: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    model_disagreement: Mapped[str | None] = mapped_column(Text, nullable=True)  # why, if the model didn't recommend them
    proposed_raise: Mapped[float | None] = mapped_column(Float, nullable=True)   # a percentage, never a salary amount
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # The review cycle it was made in (empty when no cycle was open, or for nominations made before cycles existed)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("review_cycles.id"), nullable=True, index=True)


class Decision(Base):
    """
    HR's final decision on a nomination: the decision log. It records who decided and when, what the model said
    at that moment (its score and recommendation), and the reason. A reason is required when HR disagrees with
    the model.
    """
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nomination_id: Mapped[int] = mapped_column(ForeignKey("nominations.id"), unique=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    decision: Mapped[str] = mapped_column(String(10))           # approve or reject
    model_score: Mapped[float] = mapped_column(Float)
    model_threshold: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)  # empty for decisions made before it was kept
    model_recommended: Mapped[bool] = mapped_column(Boolean)
    agrees_with_model: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_raise: Mapped[float | None] = mapped_column(Float, nullable=True)  # the % HR approved (approvals only)
    raise_reason: Mapped[str | None] = mapped_column(Text, nullable=True)       # needed when outside the pay policy
    # Finance's sign-off of the pay rise (approvals only): awaiting_finance, returned (to HR) or signed_off.
    # Empty for rejections, and for approvals made before Finance sign-off existed.
    pay_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("review_cycles.id"), nullable=True, index=True)  # its nomination's cycle
    # Finance handed the signed-off pay rise to payroll (a CSV), so it is applied once and never forgotten
    payroll_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payroll_sent_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)


class PayReview(Base):
    """
    One step in a promotion pay rise's journey, kept for audit: HR sends it to Finance, Finance signs it off or
    sends it back with a reason, HR resubmits. Nothing is ever changed or deleted. Only percentages are kept.
    """
    __tablename__ = "pay_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), index=True)
    action: Mapped[str] = mapped_column(String(20))          # submitted, returned, resubmitted or signed_off
    by_user: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    by_name: Mapped[str] = mapped_column(String(120))         # kept even if the account is renamed or deleted
    at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    raise_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecordChange(Base):
    """
    One change to an employee's work record (the model's inputs), kept for audit and never changed or deleted:
    who changed what, from what to what, why, and the readiness score before and after with the model version
    that gave both. Written when HR edits a record and when HR confirms a record correction.
    """
    __tablename__ = "record_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_by_name: Mapped[str] = mapped_column(String(120))      # kept even if the account is renamed or deleted
    source: Mapped[str] = mapped_column(String(20))                 # hr_edit or correction
    changes_json: Mapped[str] = mapped_column(Text)                 # [{"field", "old", "new"}, ...] in model units
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_before: Mapped[float] = mapped_column(Float)
    score_after: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(40))


class PayPolicy(Base):
    """
    The range a promotion pay rise should fall in, set by HR (one row). Managers propose within it; HR may go
    outside it only with a written reason. Only percentages are kept: the platform never stores salaries.
    """
    __tablename__ = "pay_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    min_raise: Mapped[float] = mapped_column(Float, default=5.0)
    max_raise: Mapped[float] = mapped_column(Float, default=15.0)

