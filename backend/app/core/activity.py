"""
The activity log: important actions, with who did them, what, and on which day.

Recorded: sign-ins (and failed sign-ins on existing accounts), account changes, nominations, promotion decisions,
and HR's actions on reports (replies, priority, status and outcome changes).

Deliberately NOT recorded: anything a reporter does (sending a report, replying, opening a case with the key,
checking text). And only the date is kept, never the time, like the reports themselves: exact sign-in times could
be lined up with a report's date to narrow down who wrote it.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base

# The actions, in the words the admin sees
ACTIONS = {
    "sign_in": "Signed in",
    "sign_in_failed": "Failed sign-in",
    "account_locked": "Account locked after too many wrong passwords",
    "password_changed": "Changed their password",
    "username_changed": "Changed their username",
    "account_created": "Created an account",
    "account_edited": "Edited an account",
    "account_deactivated": "Deactivated an account",
    "account_reactivated": "Reactivated an account",
    "account_deleted": "Deleted an account",
    "password_reset": "Reset a password",
    "permission_changed": "Changed who may view employee data",
    "profile_updated": "Updated their profile",
    "team_set": "Set a manager's team",
    "employee_added": "Added an employee",
    "employee_edited": "Edited an employee's record",
    "employees_imported": "Imported employees from a file",
    "nomination_made": "Nominated for promotion",
    "pay_policy_changed": "Changed the promotion pay-rise range",
    "decision_made": "Decided on a nomination",
    "pay_signed_off": "Signed off a promotion pay rise",
    "pay_returned": "Sent a promotion pay rise back to HR",
    "pay_resubmitted": "Sent a revised pay rise to Finance",
    "report_replied": "Replied to a report",
    "report_updated": "Updated a report",
}


class ActivityEntry(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    on_date: Mapped[date] = mapped_column(Date)                                   # the day, never the time
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(120))                           # kept even if the name changes later
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(Text, default="")


def record(db: Session, user, action: str, details: str = "") -> None:
    """Add an entry. The caller commits it together with the change it describes."""
    assert action in ACTIONS, action
    db.add(ActivityEntry(on_date=datetime.now(timezone.utc).date(), user_id=user.id if user else None,
                         user_name=user.full_name if user else "unknown", action=action, details=details))
