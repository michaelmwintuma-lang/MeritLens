"""The demo_requests table: people who asked for a demo on the public website."""
from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), index=True)
    organisation: Mapped[str] = mapped_column(String(160))
    job_title: Mapped[str] = mapped_column(String(120), default="")
    size: Mapped[str] = mapped_column(String(20))
    interest: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, default="")
    created_on: Mapped[date] = mapped_column(Date)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)  # the admin ticks this once they've replied
