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
    role: Mapped[str] = mapped_column(String(20))  # one of app.core.roles.ALL_ROLES
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # True for accounts an admin just created: the user is asked to choose their own password
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # The employee record this login belongs to (the employee directory is added in step 3)
    employee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Profile details the person keeps up to date themselves
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # How routine emails arrive: "instant" (each as it happens; the default) or "daily" (one digest each morning).
    # Emails about the account itself (password, username, email address) always arrive at once.
    email_mode: Mapped[str | None] = mapped_column(String(10), nullable=True, default="instant")
    # Two-factor sign-in (core/totp.py): the shared secret, and whether it has been confirmed and is in use
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    # The sign-in code last emailed (core/email_codes.py): only its hash, when it stops working, when it was sent,
    # and how many wrong tries it has had. A new code replaces it, so only the newest one works.
    email_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_code_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_code_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_code_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    # The first-time guide on the overview (frontend: FirstTimeGuide) was closed; My profile can show it again
    guide_done: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)

    @property
    def must_set_up_2fa(self) -> bool:
        """This role must use two-factor sign-in (REQUIRE_2FA_ROLES) and this person hasn't set it up yet."""
        from app.core.config import REQUIRE_2FA_ROLES
        return self.role in REQUIRE_2FA_ROLES and not self.totp_enabled
    photo: Mapped[str | None] = mapped_column(Text, nullable=True)  # a small picture, as a data URL (resized in the browser)
    # Admin accounts only: may view employees' records and scores (read-only). Granted by an admin, and logged.
    can_view_employees: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    # Sign-in protection: wrong passwords in a row, and until when the account is locked after too many
    failed_logins: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Raised on every password change, password reset and sign-out: login tokens made before it stop working
    token_version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
