"""
Record corrections: what can be corrected, checking a value, applying a confirmed correction, and evidence files.

Only values from the employee's own work record can be corrected (the fields HR types in), never anything the
model doesn't use and never protected characteristics, which the platform doesn't even store. Values are in the
units HR types in (93 for 93% attendance), exactly like the employee form.
"""
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import FEEDBACK_FILES_DIR
from app.feedback.models import CorrectionRequest, NominationDeferral
from app.promotion.models import Employee, Nomination
from app.promotion.records import ENTRY_FIELDS, LABELS, SCALE, to_entry

LIMITS = {name: (low, high, whole) for name, _, (low, high), whole, _ in ENTRY_FIELDS}
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
EVIDENCE_TYPES = {b"%PDF-": ("application/pdf", "pdf"), b"\xff\xd8\xff": ("image/jpeg", "jpg"),
                  b"\x89PNG\r\n\x1a\n": ("image/png", "png")}


def unprocessable(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def field_label(field: str) -> str:
    return LABELS[field]


def show(field: str, value: float | None) -> str:
    """A value as typed: '93%' for rates, '6' for counts, '81.5' for scores."""
    if value is None:
        return "–"
    text = f"{value:g}" if LIMITS[field][2] else f"{round(value, 2):g}"
    return f"{text}%" if SCALE[field] == 100 else text


def check_value(field: str, value: float) -> float:
    """A requested or verified value must be possible for that field (the same limits as the employee form)."""
    if field not in LIMITS:
        raise unprocessable("Only values from your work record can be corrected.")
    low, high, whole = LIMITS[field]
    if not low <= value <= high:
        raise unprocessable(f"{field_label(field)} must be between {low:g} and {high:g}{'%' if SCALE[field] == 100 else ''}.")
    if whole and value != int(value):
        raise unprocessable(f"{field_label(field)} must be a whole number.")
    return float(value)


def current_value(employee: Employee, field: str) -> float:
    return round(to_entry(json.loads(employee.record_json))[field], 2)


def corrected_record(employee: Employee, field: str, value: float) -> tuple[dict, dict]:
    """
    (old record, new record) with only this one field corrected; every other value stays exactly as it was. The
    value must already have passed check_value. This year's and last year's performance scores also set the
    change since last year, as on the employee form.
    """
    old = json.loads(employee.record_json)
    new = dict(old)
    last_year = old["performance_score"] - old["performance_change"]
    if field == "performance_last_year":
        new["performance_change"] = old["performance_score"] - value
    elif field == "performance_score":
        new["performance_score"], new["performance_change"] = value, value - last_year
    else:
        new[field] = value / SCALE[field]
    return old, new


def pending_for(db: Session, employee_id: int) -> list[CorrectionRequest]:
    return list(db.scalars(select(CorrectionRequest).where(CorrectionRequest.employee_id == employee_id,
                                                           CorrectionRequest.status == "pending")
                           .order_by(CorrectionRequest.created_at)))


def lift_deferrals_if_resolved(db: Session, employee_id: int) -> None:
    """Once no correction is pending for the employee, their promotion decisions are no longer on hold."""
    if pending_for(db, employee_id):
        return
    nominations = select(Nomination.id).where(Nomination.employee_id == employee_id)
    for deferral in db.scalars(select(NominationDeferral).where(NominationDeferral.nomination_id.in_(nominations),
                                                                NominationDeferral.lifted_at.is_(None))):
        deferral.lifted_at, deferral.lifted_because = datetime.now(timezone.utc), "resolved"


# ─── Evidence files ───────────────────────────────────────────────────────────
def store_evidence(data: bytes) -> tuple[str, str]:
    """Save an evidence file under a random name. Returns (stored name, content type). PDF, JPEG or PNG only."""
    if len(data) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Evidence files can be up to 10 MB.")
    kind = next((v for magic, v in EVIDENCE_TYPES.items() if data.startswith(magic)), None)
    if kind is None:
        raise unprocessable("Evidence must be a PDF, JPEG or PNG file.")
    content_type, ext = kind
    FEEDBACK_FILES_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(16)}.{ext}"
    (FEEDBACK_FILES_DIR / name).write_bytes(data)
    return name, content_type


def evidence_path(request: CorrectionRequest) -> Path | None:
    if not request.evidence_name:
        return None
    path = FEEDBACK_FILES_DIR / request.evidence_name
    return path if path.exists() else None


def describe(request: CorrectionRequest, employee_name: str | None = None) -> dict:
    """A correction request as the pages show it."""
    return {
        "id": request.id, "employee_id": request.employee_id, "employee_name": employee_name,
        "source": request.source, "created_at": request.created_at.isoformat(timespec="seconds"),
        "field": request.field, "label": field_label(request.field),
        "current_value": request.current_value, "requested_value": request.requested_value,
        "current_display": show(request.field, request.current_value),
        "requested_display": show(request.field, request.requested_value),
        "note": request.note, "has_evidence": bool(request.evidence_name), "evidence_type": request.evidence_type,
        "status": request.status, "decided_by": request.decided_by_name,
        "decided_at": request.decided_at.isoformat(timespec="seconds") if request.decided_at else None,
        "verified_value": request.verified_value,
        "verified_display": show(request.field, request.verified_value) if request.verified_value is not None else None,
        "decision_reason": request.decision_reason,
        "score_before": request.score_before, "score_after": request.score_after,
    }
