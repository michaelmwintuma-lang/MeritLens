"""
HR's side of anonymous reporting: the report inbox, one case with its triage and conversation, replies, and
updating priority, status and outcome. HR only. HR never sees anything about who the reporter is: there is
nothing stored to show.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import HR
from app.core.security import require_roles
from app.reporting.evidence import listing as evidence_listing
from app.reporting.models import Evidence, Message, Report
from app.reporting.routes import CATEGORIES, OUTCOMES, add_message, conversation
from app.reporting.triage import LABELS, LEVELS, triage
from app.core.activity import record

router = APIRouter(prefix="/api/hr/reports", tags=["reporting (HR)"])
hr_only = require_roles(HR)
STATUSES = ["open", "investigating", "closed"]


def summary(db: Session, report: Report, facts: dict | None = None) -> dict:
    """One row of the inbox. A list passes `facts` (last message and evidence count of every case, fetched at once)."""
    if facts is None:
        facts = case_facts(db, [report.case_id])
    last, evidence_count = facts["last"].get(report.case_id), facts["evidence"].get(report.case_id, 0)
    return {
        "case_id": report.case_id,
        "category": CATEGORIES[report.category],
        "priority": report.priority,
        "status": report.status,
        "created_on": report.created_on.isoformat(),
        "messages": last.number if last else 0,
        "reporter_wrote_last": bool(last and last.sender == "reporter"),
        "evidence_count": evidence_count,
    }


def case_facts(db: Session, case_ids: list[str]) -> dict:
    """For many cases in two queries: each case's last message, and how many evidence files it has."""
    from sqlalchemy import func
    last = {}
    for m in db.scalars(select(Message).where(Message.case_id.in_(case_ids)).order_by(Message.case_id, Message.number)):
        last[m.case_id] = m  # ordered by number, so the last one seen is the latest
    evidence = dict(db.execute(select(Evidence.case_id, func.count()).where(Evidence.case_id.in_(case_ids))
                               .group_by(Evidence.case_id)).all())
    return {"last": last, "evidence": evidence}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """
    What needs HR's attention: new reports nobody has answered yet, and reporters waiting for a reply. These are
    worked out from the cases themselves, so no extra record (such as the time a reporter wrote) is kept.
    """
    items = []
    reports = list(db.scalars(select(Report).where(Report.status != "closed")))
    facts = case_facts(db, [r.case_id for r in reports])
    for report in reports:
        row = summary(db, report, facts)
        if row["messages"] == 0:
            items.append({"case_id": report.case_id, "kind": "new_report", "priority": report.priority,
                          "text": f"New {row['category'].lower()} report ({LABELS[report.priority]} priority)"})
        elif row["reporter_wrote_last"]:
            items.append({"case_id": report.case_id, "kind": "reporter_replied", "priority": report.priority,
                          "text": "The reporter replied and is waiting for you"})
    return sorted(items, key=lambda i: -LEVELS.index(i["priority"]))


@router.get("")
def inbox(db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """Every report: open cases first, then by priority (high first), newest first."""
    reports = db.scalars(select(Report)).all()
    order = lambda r: (r.status == "closed", -LEVELS.index(r.priority), -r.created_on.toordinal())  # noqa: E731
    facts = case_facts(db, [r.case_id for r in reports])
    return [summary(db, r, facts) for r in sorted(reports, key=order)]


def get_report(db: Session, case_id: str) -> Report:
    report = db.get(Report, case_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such case.")
    return report


@router.get("/{case_id}")
def open_report(case_id: str, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """One case: the text, why triage suggested its priority, the conversation, and the options to update it."""
    report = get_report(db, case_id)
    return {
        **summary(db, report),
        "category_code": report.category,
        "text": report.text,
        "suggested_priority": report.suggested_priority,
        "triage": triage(report.text, report.category),
        "outcome": report.outcome,
        "conversation": conversation(db, report.case_id),
        "evidence": evidence_listing(db, report.case_id),
        "options": {"priorities": LEVELS, "statuses": STATUSES, "outcomes": OUTCOMES},
    }


class ReplyIn(BaseModel):
    text: str = Field(min_length=2, max_length=3000)


@router.post("/{case_id}/messages", status_code=status.HTTP_201_CREATED)
def reply(case_id: str, body: ReplyIn, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """HR replies. The reporter sees it from "Investigator", never a name."""
    report = get_report(db, case_id)
    if report.status == "closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This case is closed.")
    add_message(db, report.case_id, "investigator", body.text)
    if report.status == "open":
        report.status = "investigating"  # replying means the case is being looked at
    record(db, user, "report_replied", report.case_id)
    db.commit()
    return {"conversation": conversation(db, report.case_id), "status": report.status}


class UpdateIn(BaseModel):
    priority: str | None = None
    status: str | None = None
    outcome: str | None = None


@router.patch("/{case_id}")
def update(case_id: str, body: UpdateIn, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """
    Change the priority, the status, or record the outcome. Closing a case needs an outcome. The outcome stays
    in the reporting part: it is never used by the promotion model.
    """
    report = get_report(db, case_id)
    if body.priority is not None:
        if body.priority not in LEVELS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Priority must be one of: {', '.join(LEVELS)}.")
        report.priority = body.priority
    if body.outcome is not None:
        if body.outcome not in OUTCOMES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown outcome.")
        report.outcome = body.outcome
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Status must be one of: {', '.join(STATUSES)}.")
        if body.status == "closed" and not report.outcome:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an outcome before closing the case.")
        report.status = body.status
        if body.status != "closed":
            report.outcome = report.outcome if body.outcome else None  # reopening clears an old outcome
    changes = ", ".join(f"{k} {v}" for k, v in body.model_dump(exclude_none=True).items())
    record(db, user, "report_updated", f"{report.case_id}: {changes}")
    db.commit()
    return open_report(case_id, db)
