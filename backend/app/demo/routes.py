"""
"Book a demo" from the public website.

Anyone can send a request (no sign-in). It's saved, emailed to DEMO_INBOX (by default the platform's Gmail) with
Reply-To set to the visitor, and listed for the admin. Spam protection, kept simple:
- a hidden "website" box that people never see but form-filling robots do fill in: such requests are thanked and
  quietly dropped
- at most 3 requests per email address per day, and at most 30 in total per hour
No IP addresses are stored, in keeping with the rest of the platform.
"""
import time
from collections import deque
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.config import DEMO_INBOX
from app.core.database import get_db
from app.core.roles import ADMIN
from app.core.security import require_roles
from app.demo.models import DemoRequest

router = APIRouter(prefix="/api/public/demo-requests", tags=["demo"])
admin_router = APIRouter(prefix="/api/admin/demo-requests", tags=["demo"])
admin_only = require_roles(ADMIN)

SIZES = ["1–49", "50–249", "250–999", "1,000+"]
INTERESTS = ["Promotion readiness", "Employee feedback", "Both"]
PER_EMAIL_PER_DAY = 3
PER_HOUR = 30
_recent = deque()  # times of recent requests, for the hourly limit (kept in memory only)


class DemoRequestIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    organisation: str = Field(min_length=2, max_length=160)
    job_title: str = Field(default="", max_length=120)
    size: str
    interest: str
    message: str = Field(default="", max_length=1000)
    website: str = ""  # the hidden box: must stay empty


THANKS = {"ok": True, "message": "Thank you! We'll email you within two working days to arrange a time."}


@router.post("", status_code=status.HTTP_201_CREATED)
def request_demo(body: DemoRequestIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Save a demo request and email it to the demo inbox."""
    if body.website:  # a robot filled in the hidden box: look successful, save nothing
        return THANKS
    if body.size not in SIZES or body.interest not in INTERESTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please choose an organisation size and what you're interested in.")

    now = time.monotonic()
    while _recent and now - _recent[0] > 3600:
        _recent.popleft()
    email = body.email.strip().lower()
    today_from_email = db.scalar(select(func.count()).select_from(DemoRequest)
                                 .where(DemoRequest.email == email, DemoRequest.created_on == date.today()))
    if len(_recent) >= PER_HOUR or today_from_email >= PER_EMAIL_PER_DAY:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "We've already received your request. We'll be in touch soon.")
    _recent.append(now)

    request = DemoRequest(name=body.name.strip(), email=email, organisation=body.organisation.strip(),
                          job_title=body.job_title.strip(), size=body.size, interest=body.interest,
                          message=body.message.strip(), created_on=date.today())
    db.add(request)
    db.commit()
    mail = templates.demo_request(request.name, request.email, request.organisation, request.job_title,
                                  request.size, request.interest, request.message)
    background.add_task(mailer.send, DEMO_INBOX or "demo-requests", mail)
    return THANKS


@router.get("/options")
def options():
    """The choices the form offers."""
    return {"sizes": SIZES, "interests": INTERESTS}


# ─── The admin's list ─────────────────────────────────────────────────────────
@admin_router.get("")
def list_requests(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Every demo request, newest first; unhandled ones first."""
    rows = db.scalars(select(DemoRequest).order_by(DemoRequest.handled, DemoRequest.created_on.desc(), DemoRequest.id.desc()))
    return [{"id": r.id, "name": r.name, "email": r.email, "organisation": r.organisation, "job_title": r.job_title,
             "size": r.size, "interest": r.interest, "message": r.message, "created_on": r.created_on.isoformat(),
             "handled": r.handled} for r in rows]


class HandledIn(BaseModel):
    handled: bool


@admin_router.patch("/{request_id}")
def mark_handled(request_id: int, body: HandledIn, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Tick a request off once it's been answered (or untick it)."""
    request = db.get(DemoRequest, request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such request.")
    request.handled = body.handled
    db.commit()
    return {"id": request.id, "handled": request.handled}
