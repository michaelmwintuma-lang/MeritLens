"""
The reporting tables: reports and their conversations. Separate from the promotion tables, and never read by
the promotion code.

What is deliberately NOT stored: who sent a report or a reporter message (no user, account or employee column),
the original text, exact times (only dates), IP addresses or browser details, and the secret key (only its hash).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"
    # SQLite normally numbers rows in the order they're added. Without that hidden number, the order of reports
    # can't be lined up against who was signed in at the time.
    __table_args__ = {"sqlite_with_rowid": False}

    case_id: Mapped[str] = mapped_column(String(20), primary_key=True)   # random, e.g. R-7KQ2-M9XD
    category: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)                             # the anonymised text the reporter approved
    created_on: Mapped[date] = mapped_column(Date)                       # the day only, never the time
    key_hash: Mapped[str] = mapped_column(String(200))                   # hash of the secret key
    # Triage: the priority the keyword rules suggested, and the priority HR has set (they can change it)
    suggested_priority: Mapped[str] = mapped_column(String(10), default="low")
    priority: Mapped[str] = mapped_column(String(10), default="low")    # low, medium or high
    status: Mapped[str] = mapped_column(String(20), default="open")     # open, investigating or closed
    outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)  # set when the case is closed
    # Protection against guessing keys: after 5 wrong keys the case is locked for 15 minutes
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Message(Base):
    """
    One message in a case's conversation. The sender is only "reporter" or "investigator": the reporter sees
    HR as "Investigator", and HR sees the reporter as "Reporter". Only the date is kept; the order comes from
    a running number within the case.
    """
    __tablename__ = "report_messages"
    __table_args__ = {"sqlite_with_rowid": False}

    case_id: Mapped[str] = mapped_column(ForeignKey("reports.case_id"), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)       # 1, 2, 3... within the case
    sender: Mapped[str] = mapped_column(String(15))                      # reporter or investigator
    text: Mapped[str] = mapped_column(Text)
    sent_on: Mapped[date] = mapped_column(Date)


class Evidence(Base):
    """
    A photo or video the reporter attached to their case. The file itself is in EVIDENCE_DIR under a random name;
    its hidden details (location, device, owner, time taken) were removed before it was saved. The original file
    name is not kept (it often contains a name or a date), and only the day it was added.
    """
    __tablename__ = "report_evidence"
    __table_args__ = {"sqlite_with_rowid": False}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)         # random
    case_id: Mapped[str] = mapped_column(ForeignKey("reports.case_id"), index=True)
    number: Mapped[int] = mapped_column(Integer)                          # 1, 2, 3... within the case
    kind: Mapped[str] = mapped_column(String(10))                         # photo or video
    content_type: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)                            # bytes, after cleaning
    stored_name: Mapped[str] = mapped_column(String(80))
    added_on: Mapped[date] = mapped_column(Date)

