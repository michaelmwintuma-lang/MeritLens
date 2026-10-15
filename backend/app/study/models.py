"""
The user study's tables: one session per participant (a code like P3, never a name), the time and outcome of each
task, and their questionnaire answers. Nothing here identifies a person, and nothing here reaches the model or the
promotion pages: it is evaluation data, exported to backend/evaluation/ for evaluation/user_test.py.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)                 # P1, P2, ...
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)            # the facilitator's link (only its hash)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    roles_played: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)            # "the most confusing moment"


class StudyTask(Base):
    __tablename__ = "study_tasks"
    __table_args__ = (UniqueConstraint("session_id", "task"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    task: Mapped[str] = mapped_column(String(5))                                 # T1 ... T11
    completed: Mapped[str] = mapped_column(String(5))                            # yes, help or no
    seconds: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class StudyAnswer(Base):
    __tablename__ = "study_answers"
    __table_args__ = (UniqueConstraint("session_id", "item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    item: Mapped[str] = mapped_column(String(5))                                 # q1-q10, e1-e4, i1-i4, p1-p4
    value: Mapped[int] = mapped_column(Integer)                                  # 1 (strongly disagree) to 5
