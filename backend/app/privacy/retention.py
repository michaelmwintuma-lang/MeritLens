"""
Retention: personal data is kept only as long as it is needed, then removed automatically (the scheduler runs this
once a day; the periods are set in config.py and listed on the public privacy page).

- Rating comments: the comment text is removed (the 1-5 answers and flags stay, for the dashboard's totals).
- Notifications in the bell, and the email delivery log.
- Activity-log entries.
The audit trail is never pruned: it is the record of who decided what, and its hash chain must stay whole.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.core.activity import ActivityEntry
from app.core.config import RETENTION_DAYS
from app.core.mailer import EmailLog
from app.core.notifications import Notification
from app.feedback.models import ExplanationRating


def run(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Remove what is past its retention period. Returns how many of each were removed."""
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    before = lambda kind: now - timedelta(days=RETENTION_DAYS[kind])  # noqa: E731
    removed = {
        "rating_comments": db.execute(update(ExplanationRating).where(
            ExplanationRating.created_at < before("rating_comments"), ExplanationRating.comment.is_not(None)).values(comment=None)).rowcount,
        "notifications": db.execute(delete(Notification).where(Notification.created_at < before("notifications"))).rowcount,
        "email_log": db.execute(delete(EmailLog).where(EmailLog.created_at < before("email_log"),
                                                       EmailLog.status.in_(("sent", "saved", "gave_up", "in_digest")))).rowcount,
        "activity_log": db.execute(delete(ActivityEntry).where(ActivityEntry.on_date < before("activity_log").date())).rowcount,
    }
    db.commit()
    return removed
