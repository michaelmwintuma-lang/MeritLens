"""The promotion part's tables: the employee directory, nominations, and decisions (the decision log)."""
import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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

    @property
    def record(self) -> dict:
        """The work record as a dictionary, including department."""
        return {**json.loads(self.record_json), "department": self.department}


class Nomination(Base):
    """A manager proposes a team member for promotion, with a short reason. HR decides."""
    __tablename__ = "nominations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    nominated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved or rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    model_recommended: Mapped[bool] = mapped_column(Boolean)
    agrees_with_model: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
