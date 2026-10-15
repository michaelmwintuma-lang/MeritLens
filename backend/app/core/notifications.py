"""
The notification centre: one line in a person's bell for each thing that happened that they may need to act on.

A notification is added when an email with a "notice" goes to someone with an account (mailer.py), so the bell and
the email always come from the same event. The bell also shows what is waiting right now (worked out live, e.g.
corrections in HR's queue); these stored notifications are its history, read or unread. Only the line, an optional
detail and a link to the page are kept: never anything an employee wrote, nor scores.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, func, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base, get_db
from app.core.security import get_current_user

KEEP = 30  # how many recent notifications the bell lists


def now() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(String(200))
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)   # a page inside the app, e.g. /finance
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def add(db: Session, user_id: int, text: str, link: str | None) -> Notification:
    """Add one notification. The caller commits."""
    entry = Notification(user_id=user_id, text=text[:200], link=link)
    db.add(entry)
    return entry


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def mine(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Your most recent notifications, newest first, and how many are unread."""
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(KEEP))
    unread = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)))
    return {"unread": unread, "items": [{"id": n.id, "text": n.text, "link": n.link, "read": n.read_at is not None,
                                         "at": n.created_at.isoformat(timespec="seconds")} for n in rows]}


class ReadIn(BaseModel):
    ids: list[int] | None = None  # empty: all of them


@router.post("/read")
def mark_read(body: ReadIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Mark your notifications read (these ones, or all)."""
    query = update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    if body.ids:
        query = query.where(Notification.id.in_(body.ids))
    db.execute(query.values(read_at=now()))
    db.commit()
    return {"ok": True}
