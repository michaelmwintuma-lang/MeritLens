"""
The employee's side of the feedback channel: respond to your own explanation.

1. Rate it: clear? useful? (1-5), and mark any factor that seems wrong or unfair, with an optional comment.
2. Ask HR to correct a value in your work record, with evidence (a note, and optionally a file).
3. (Report an unfair assessment anonymously: that is the reporting part, /report, which never links to you.)

Only employees use these endpoints, and only about themselves. Nothing here changes a score: a rating is stored
for HR's aggregate view, and a correction request waits for HR. Only HR confirming a correction changes the
record (routes_hr.py).
"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import hr_contacts
from app.accounts.models import User
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import record
from app.core.database import get_db
from app.core.roles import EMPLOYEE
from app.core.security import require_roles
from app.feedback import corrections
from app.feedback.models import CorrectionRequest, ExplanationRating
from app.promotion.features import MODEL_FEATURES
from app.promotion.models import Employee
from app.promotion.records import field_list
from app.promotion.routes import model

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
employees_only = require_roles(EMPLOYEE)


def own_employee(user: User, db: Session) -> Employee:
    """The signed-in employee's own record. Feedback is always about yourself."""
    employee = db.get(Employee, user.employee_id) if user.employee_id else None
    if employee is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your account isn't linked to an employee record yet.")
    return employee


# ─── 1. Rating the explanation ────────────────────────────────────────────────
class FlagIn(BaseModel):
    feature: str
    kind: str = Field(pattern="^(wrong|unfair)$")


class RatingIn(BaseModel):
    clarity: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    flagged: list[FlagIn] = Field(default_factory=list, max_length=len(MODEL_FEATURES))
    comment: str | None = Field(default=None, max_length=1000)


def rating_out(rating: ExplanationRating | None) -> dict | None:
    if rating is None:
        return None
    return {"clarity": rating.clarity, "usefulness": rating.usefulness, "flagged": json.loads(rating.flagged_json),
            "comment": rating.comment, "model_version": rating.model_version,
            "created_at": rating.created_at.isoformat(timespec="seconds")}


@router.get("/ratings/mine")
def my_rating(user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """Your rating of the explanation from the current model, if you have given one."""
    employee = own_employee(user, db)
    rating = db.scalar(select(ExplanationRating).where(ExplanationRating.employee_id == employee.id,
                                                       ExplanationRating.model_version == model().version))
    return {"rating": rating_out(rating)}


@router.post("/ratings", status_code=status.HTTP_201_CREATED)
def rate(body: RatingIn, user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """
    Rate your explanation. Stored with the model version and the score it explained (worked out here, not taken
    from the page). Rating the same model's explanation again replaces your earlier rating. Never changes a score.
    """
    employee = own_employee(user, db)
    flagged = {}
    for flag in body.flagged:
        if flag.feature not in MODEL_FEATURES:
            raise corrections.unprocessable("You can only mark factors shown in your explanation.")
        flagged[flag.feature] = flag.kind  # one mark per factor
    live = model()
    rating = db.scalar(select(ExplanationRating).where(ExplanationRating.employee_id == employee.id,
                                                       ExplanationRating.model_version == live.version))
    if rating is None:
        rating = ExplanationRating(employee_id=employee.id, model_version=live.version)
        db.add(rating)
    rating.score = round(live.score(employee.record), 4)
    rating.clarity, rating.usefulness = body.clarity, body.usefulness
    rating.flagged_json = json.dumps([{"feature": f, "kind": k} for f, k in flagged.items()])
    rating.comment = (body.comment or "").strip() or None
    db.commit()
    return {"rating": rating_out(rating)}


# ─── 2. Asking for a record correction ────────────────────────────────────────
@router.get("/fields")
def correctable_fields(user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """The values in your work record you can ask HR to correct, with what the record says now."""
    employee = own_employee(user, db)
    pending = {r.field for r in corrections.pending_for(db, employee.id)}
    return [{**f, "current": corrections.current_value(employee, f["name"]), "pending": f["name"] in pending}
            for f in field_list(model().stats)]


class CorrectionIn(BaseModel):
    field: str
    requested_value: float
    note: str = Field(min_length=10, max_length=2000)


@router.post("/corrections", status_code=status.HTTP_201_CREATED)
def request_correction(body: CorrectionIn, background: BackgroundTasks, user: User = Depends(employees_only),
                       db: Session = Depends(get_db)):
    """Ask HR to correct one value in your record. HR checks the evidence; nothing changes until HR confirms."""
    employee = own_employee(user, db)
    value = corrections.check_value(body.field, body.requested_value)
    current = corrections.current_value(employee, body.field)
    if value == current:
        raise corrections.unprocessable("That is already the value in your record.")
    if any(r.field == body.field for r in corrections.pending_for(db, employee.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a request about this value waiting for HR.")
    request = CorrectionRequest(employee_id=employee.id, source="employee", requested_by=user.id, field=body.field,
                                current_value=current, requested_value=value, note=body.note.strip())
    db.add(request)
    record(db, user, "correction_requested", corrections.field_label(body.field))
    db.commit()
    for email, hr_name in hr_contacts(db):
        background.add_task(mailer.send, email, templates.correction_received(hr_name, employee.full_name,
                                                                              corrections.field_label(body.field)))
    return corrections.describe(request)


def own_request(request_id: int, user: User, db: Session) -> CorrectionRequest:
    request = db.get(CorrectionRequest, request_id)
    if request is None or request.employee_id != user.employee_id or request.source != "employee":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such request.")
    return request


@router.post("/corrections/{request_id}/evidence")
def add_evidence(request_id: int, file: UploadFile = File(...), user: User = Depends(employees_only),
                 db: Session = Depends(get_db)):
    """Attach one file (PDF, JPEG or PNG, up to 10 MB) to your pending request. A new file replaces the old one."""
    request = own_request(request_id, user, db)
    if request.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "HR has already decided on this request.")
    name, content_type = corrections.store_evidence(file.file.read(corrections.MAX_EVIDENCE_BYTES + 1))
    if (old := corrections.evidence_path(request)) is not None:
        old.unlink(missing_ok=True)
    request.evidence_name, request.evidence_type = name, content_type
    db.commit()
    return corrections.describe(request)


@router.get("/corrections/{request_id}/evidence")
def my_evidence(request_id: int, user: User = Depends(employees_only), db: Session = Depends(get_db)):
    request = own_request(request_id, user, db)
    return evidence_file(request)


def evidence_file(request: CorrectionRequest) -> FileResponse:
    path = corrections.evidence_path(request)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No file is attached.")
    return FileResponse(path, media_type=request.evidence_type, headers={
        "Content-Disposition": f'inline; filename="correction-{request.id}-evidence.{path.suffix[1:]}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/corrections/mine")
def my_corrections(user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """Your correction requests, newest first, with HR's decisions."""
    employee = own_employee(user, db)
    rows = db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == employee.id)
                      .order_by(CorrectionRequest.created_at.desc(), CorrectionRequest.id.desc()))
    return [mine(corrections.describe(r)) for r in rows]


def mine(row: dict) -> dict:
    """A re-appraisal's note is HR's own; the employee sees only what changed and why HR decided."""
    if row["source"] == "reappraisal":
        row.update(note="HR reviewed this value in a re-appraisal.", has_evidence=False)
    return row


# ─── Notifications ────────────────────────────────────────────────────────────
@router.get("/notifications")
def notifications(user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """Decisions on your record (your requests, and corrections HR made after a re-appraisal) not yet seen."""
    if not user.employee_id:
        return []
    rows = db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == user.employee_id,
                                                      CorrectionRequest.status != "pending",
                                                      CorrectionRequest.employee_seen.is_not(True)))
    return [{"id": r.id, "status": r.status, "label": corrections.field_label(r.field)} for r in rows]


@router.post("/notifications/seen")
def mark_seen(user: User = Depends(employees_only), db: Session = Depends(get_db)):
    """You've seen the decisions on your record."""
    for r in db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == user.employee_id,
                                                        CorrectionRequest.status != "pending")):
        r.employee_seen = True
    db.commit()
    return {"ok": True}
