"""The users table: one row per login."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)  # for the welcome email
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # employee, manager, hr or admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # True for accounts an admin just created: the user is asked to choose their own password
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # The employee record this login belongs to (the employee directory is added in step 3)
    employee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Profile details the person keeps up to date themselves
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    photo: Mapped[str | None] = mapped_column(Text, nullable=True)  # a small picture, as a data URL (resized in the browser)
    # Admin accounts only: may view employees' records and scores (read-only). Granted by an admin, and logged.
    can_view_employees: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
