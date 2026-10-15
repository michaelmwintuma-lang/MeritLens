"""
Governance tables: who released which model version, and equality-monitoring data for the live fairness check.

- ModelRelease: every time a trained model version is made live (or an older one restored), with the person who
  approved it, when, why, and which version it replaced. A model goes live only through a named person.
- EqualityMonitoring: gender, age band and education for each employee, kept apart from the employee directory
  and used ONLY to check, in aggregate, whether the model's recommendations and people's decisions treat groups
  alike. Nothing here is ever shown per person, groups under 5 are never shown, and the promotion code can't read
  it (tests/test_isolation.py; with PostgreSQL, its database role can't either). Age is kept as a band, not a
  birth date or an age.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ModelRelease(Base):
    __tablename__ = "model_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(40), index=True)
    previous_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    released_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    released_by_name: Mapped[str] = mapped_column(String(120))
    released_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    note: Mapped[str] = mapped_column(Text)


class EqualityMonitoring(Base):
    __tablename__ = "equality_monitoring"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)          # None: not given
    age_band: Mapped[str | None] = mapped_column(String(20), nullable=True)        # "under 40" or "40+"
    education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=now)
