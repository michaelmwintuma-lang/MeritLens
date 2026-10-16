"""
A development plan: goals an employee works towards with their manager, often taken from the readiness tips
("increase training hours from 20 to 35"). Either of them, or HR, can add a goal and tick it off.

Kept apart from the model on purpose: goals are never one of its inputs, and the promotion code never reads this
table (tests/test_isolation.py checks it), so writing a goal down, or ticking it off, can't change a score. Only the
work record changes a score, as always.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class DevelopmentGoal(Base):
    __tablename__ = "development_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    feature: Mapped[str | None] = mapped_column(String(60), nullable=True)   # the input a tip was about, if any
    target: Mapped[float | None] = mapped_column(Float, nullable=True)       # the tip's target value, if any
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    due: Mapped[date | None] = mapped_column(Date, nullable=True)
    added_by_name: Mapped[str] = mapped_column(String(120))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    done_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
