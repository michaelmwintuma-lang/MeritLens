"""
Anonymous reporting API.

Only signed-in employees and managers can use it, which keeps outsiders out. (HR handles reports in the report
inbox, and admins manage accounts.) But the reporter's identity is used for nothing else: these endpoints never
read who the user is, never store it, and never log it.
A report is linked to its reporter only by the secret key, which only the reporter has.

1. preview: the reporter's text is anonymised and sent back for review. Nothing is stored.
2. submit:  the approved text is saved; the reporter receives a case ID and a secret key, once.
3. access:  case ID + key opens the case later. Wrong attempts lock the case for 15 minutes.
4. messages: the reporter replies to the investigator, with the same anonymising rules.
(Photos and videos as evidence: routes_evidence.py, also opened with the case ID and key.)

The server never checks cases in bulk or in the background: a reporter opens one case at a time by typing its ID
and key. Keys are never kept by the website either (see frontend/src/keyStore.js).
"""
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import REPORTER_ROLES
from app.core.security import hash_password, require_roles, verify_password
from app.promotion.models import Employee
from app.reporting.anonymiser import anonymise, still_identifying
from app.reporting.evidence import listing as evidence_listing
from app.reporting.models import Message, Report
from app.reporting.triage import triage
from app.accounts.contacts import hr_contacts
from app.core import email_templates as templates
from app.core import mailer

router = APIRouter(prefix="/api/reports", tags=["reporting"])
# Employees and managers report; HR handles reports in their inbox, and admins manage accounts
reporters = require_roles(*REPORTER_ROLES)

# What can be reported, in groups for the form. Reporting is part of the employee feedback channel: its purpose is
# to raise an unfair promotion assessment, or anything else that went wrong at work, without being identified.
# The keys are stored with each report, so they never change (labels can).
CATEGORY_GROUPS = [
    ("Promotion and appraisal", [
        ("biased_rating", "Biased rating or appraisal"),
        ("favouritism", "Favouritism"),
        ("discrimination", "Discrimination"),
        ("wrong_record", "Wrong or missing record"),
    ]),
    ("Anything else", [
        ("other_concern", "Other workplace concern"),
    ]),
]
# The categories offered before reporting was aligned with the feedback channel. Reports already saved keep
# showing theirs; new reports use CATEGORY_GROUPS above. Some have a minimum priority: see app/reporting/triage.py.
EARLIER_CATEGORY_GROUPS = [
    ("How people are treated", [
        ("harassment", "Harassment"),
        ("sexual_harassment", "Sexual harassment or assault"),
        ("discrimination", "Discrimination"),
        ("bullying", "Bullying or intimidation"),
        ("violence", "Violence or threats of violence"),
        ("retaliation", "Retaliation for speaking up"),
        ("abuse_of_power", "Abuse of power or favouritism"),
    ]),
    ("Safety and wellbeing", [
        ("safety", "Health and safety hazard"),
        ("harm_risk", "Risk of self-harm or harm to others"),
        ("substance", "Drug or alcohol misuse at work"),
        ("working_conditions", "Excessive hours, workload or unsafe working conditions"),
    ]),
    ("Honesty and the law", [
        ("ethics", "Fraud, bribery or corruption"),
        ("theft", "Theft or misuse of company property"),
        ("conflict_of_interest", "Conflict of interest"),
        ("data_privacy", "Data protection or privacy breach"),
        ("employment_rights", "Unfair pay, denied leave or employment rights"),
        ("legal_breach", "Breaking the law or company policy"),
        ("environment", "Environmental harm"),
    ]),
    ("Anything else", [
        ("other", "Something else"),
    ]),
]
REPORTABLE = {key for _, items in CATEGORY_GROUPS for key, _ in items}
CATEGORIES = {key: label for _, items in EARLIER_CATEGORY_GROUPS + CATEGORY_GROUPS for key, label in items}
OUTCOMES = {
    "substantiated": "Concern upheld",
    "not_substantiated": "Concern not upheld",
    "inconclusive": "Not enough evidence either way",
    "resolved": "Resolved informally",
    # The concern was about an assessment, and it was unfair: HR can then open a re-appraisal of the affected value
    # (a record correction that is never linked to the report)
    "rating_unfair": "Rating found unfair",
}
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
SAME_ERROR = ("That case ID and key don't match a report, or the case is locked for 15 minutes after too many "
              "wrong attempts.")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, which are easy to mix up when copying
# A hash of a random key, used to make checks for unknown cases take as long as checks for real ones
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def random_code(groups: int, size: int = 4) -> str:
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(size)) for _ in range(groups))


def directory_names(db: Session) -> list[str]:
    """Everyone the anonymiser should recognise: the employee directory and every account holder."""
    names = [e.full_name for e in db.scalars(select(Employee))]
    return names + [u.full_name for u in db.scalars(select(User))]


def today() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/categories")
def categories(_: User = Depends(reporters)):
    """The categories in their groups, for the form's drop-down."""
    return [{"group": group, "items": [{"value": key, "label": label} for key, label in items]} for group, items in CATEGORY_GROUPS]


# ─── 1. Preview (nothing stored) ──────────────────────────────────────────────
class TextIn(BaseModel):
    text: str = Field(min_length=20, max_length=5000)


@router.post("/preview")
def preview(body: TextIn, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """The anonymised version for the reporter to review and edit. The original is neither stored nor logged."""
    return anonymise(body.text, directory_names(db))


# ─── 2. Submit ────────────────────────────────────────────────────────────────
class ReportIn(BaseModel):
    category: str
    text: str = Field(min_length=20, max_length=5000)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit(body: ReportIn, background: BackgroundTasks, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """
    Save the approved, anonymised text. The signed-in user is checked (organisation members only) but is not
    passed on or saved anywhere. Returns the case ID and the secret key; the key is never shown again.
    """
    if body.category not in REPORTABLE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please choose one of the categories.")
    # The reporter may have edited the cleaned text; make sure no name, email, phone or date crept back in
    leftovers = still_identifying(body.text, directory_names(db))
    if leftovers:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "The text still contains details that could identify someone. Please check it again.")

    case_id = f"R-{random_code(2)}"
    while db.get(Report, case_id):  # astronomically rare, but never reuse an ID
        case_id = f"R-{random_code(2)}"
    key = random_code(4)
    suggested = triage(body.text, body.category)["priority"]
    db.add(Report(case_id=case_id, category=body.category, text=body.text.strip(), created_on=today(),
                  key_hash=hash_password(key), suggested_priority=suggested, priority=suggested))
    db.commit()
    # Tell HR a report is waiting: only the case ID, category and priority, never the text or anything about the reporter
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.report_alert(hr_name, case_id, CATEGORIES[body.category], suggested))
    return {"case_id": case_id, "key": key, "created_on": today().isoformat()}


# ─── 3. Access with case ID and key ───────────────────────────────────────────
class AccessIn(BaseModel):
    case_id: str
    key: str


def open_case(case_id: str, key: str, db: Session) -> Report:
    """
    The report, if the case ID and key match and the case isn't locked. Every failure gives the same message,
    so nobody can tell whether a case ID exists. Five wrong keys lock the case for 15 minutes.
    """
    report = db.get(Report, case_id.strip().upper())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if report is None:
        verify_password(key, _DUMMY_HASH)  # take the same time as a real check
        raise HTTPException(status.HTTP_403_FORBIDDEN, SAME_ERROR)
    if report.locked_until and report.locked_until > now:
        raise HTTPException(status.HTTP_403_FORBIDDEN, SAME_ERROR)
    if not verify_password(key.strip().upper(), report.key_hash):
        report.failed_attempts += 1
        if report.failed_attempts >= MAX_ATTEMPTS:
            report.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            report.failed_attempts = 0
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, SAME_ERROR)
    report.failed_attempts = 0
    db.commit()
    return report


def conversation(db: Session, case_id: str) -> list[dict]:
    """The case's messages in order. Senders appear only as "Reporter" or "Investigator"."""
    messages = db.scalars(select(Message).where(Message.case_id == case_id).order_by(Message.number))
    return [{"number": m.number, "sender": m.sender, "text": m.text, "sent_on": m.sent_on.isoformat()} for m in messages]


def add_message(db: Session, case_id: str, sender: str, text: str) -> None:
    """Append a message, numbered after the last one in the case."""
    last = db.scalar(select(Message.number).where(Message.case_id == case_id).order_by(Message.number.desc()).limit(1))
    db.add(Message(case_id=case_id, number=(last or 0) + 1, sender=sender, text=text.strip(), sent_on=today()))


@router.post("/access")
def access(body: AccessIn, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """The reporter's own view of their case, with the conversation. Priority and HR's notes are not shown."""
    report = open_case(body.case_id, body.key, db)
    return {"case_id": report.case_id, "category": CATEGORIES[report.category], "text": report.text,
            "created_on": report.created_on.isoformat(), "status": report.status,
            "outcome": OUTCOMES.get(report.outcome), "messages": conversation(db, report.case_id),
            "evidence": evidence_listing(db, report.case_id)}


# ─── 4. The reporter replies ──────────────────────────────────────────────────
class ReporterMessageIn(AccessIn):
    text: str = Field(min_length=2, max_length=3000)


@router.post("/messages", status_code=status.HTTP_201_CREATED)
def reporter_message(body: ReporterMessageIn, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """
    The reporter writes to the investigator. Like the report itself, the message must already be anonymised
    (the page runs it through /preview first); one that still contains a name, email, phone or date is refused.
    """
    report = open_case(body.case_id, body.key, db)
    if report.status == "closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This case is closed.")
    if still_identifying(body.text, directory_names(db)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "The message still contains details that could identify someone. Please check it again.")
    add_message(db, report.case_id, "reporter", body.text)
    db.commit()
    return {"messages": conversation(db, report.case_id)}
