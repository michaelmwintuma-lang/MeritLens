"""
Governance API: the model registry (and its human release step), the live fairness monitor, and the audit trail.

Who sees what:
- Model registry: HR, admins and the compliance auditor can read every version's model card. Only HR releases a
  version, with a written note; nobody can release a version that failed the fairness check.
- Live fairness: HR, admins and the auditor; totals per group only, groups under 5 never shown.
- Audit trail: the auditor and admins, read-only, with a check that the hash chain is intact.
"""
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import approvals, audit
from app.core.activity import record
from app.core.database import get_db
from app.core.roles import ADMIN, AUDITOR, HR
from app.core.security import require_roles
from app.governance import monitoring, registry
from app.promotion.models import ReviewCycle

router = APIRouter(prefix="/api/governance", tags=["governance"])
readers = require_roles(HR, ADMIN, AUDITOR)


# ─── Model registry ───────────────────────────────────────────────────────────
class ModelVersionOut(BaseModel):
    version: str
    model: str
    trained_at: str
    status: str = Field(description="live, candidate (waiting for release), retired (live before) or blocked (failed fairness)")
    threshold: float
    roc_auc: float | None
    pr_auc: float | None
    fairness_passes: bool
    lowest_fairness_ratio: float | None
    released_by: str | None
    released_at: str | None
    data_name: str | None


class ReleaseOut(BaseModel):
    version: str
    previous_version: str | None
    released_by: str
    released_at: str
    note: str


class ModelCardOut(BaseModel):
    version: str
    status: str
    card: dict[str, Any]
    releases: list[ReleaseOut]


class ReleaseIn(BaseModel):
    note: str = Field(max_length=2000)


@router.get("/models", response_model=list[ModelVersionOut])
def models(db: Session = Depends(get_db), _: User = Depends(readers)):
    """Every trained version, newest first: which is live, which wait for release, which are blocked."""
    return registry.list_versions(db)


@router.get("/models/{version}", response_model=ModelCardOut)
def model_card(version: str, db: Session = Depends(get_db), _: User = Depends(readers)):
    """One version's model card and its release history."""
    try:
        data = registry.card(version)
    except ValueError:
        data = None
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such model version.")
    row = next(r for r in registry.list_versions(db) if r["version"] == version)
    return {"version": version, "status": row["status"], "card": data, "releases": registry.release_history(db, version)}


def release_errors(action):
    """Run a registry step, turning its refusals into HTTP answers."""
    try:
        return action()
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    except PermissionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error))
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.post("/models/{version}/release", response_model=ModelCardOut,
             responses={202: {"description": "Waiting for a second HR person's approval (FOUR_EYES)"}})
def release(version: str, body: ReleaseIn, background: BackgroundTasks, db: Session = Depends(get_db),
            user: User = Depends(require_roles(HR))):
    """
    Make this version the live model, after reading its card. HR only, with a note of at least 20 characters.
    Releasing an older version is how a release is rolled back. With FOUR_EYES on, this asks a second HR person.
    """
    if approvals.on():
        release_errors(lambda: registry.check_release(db, version, body.note))
        entry = approvals.request(db, background, "model_release", version, f"Release model version {version}: {body.note.strip()}",
                                  {"note": body.note}, user)
        db.commit()
        return approvals.pending_response(entry)
    release_errors(lambda: registry.release(db, version, user, body.note))
    record(db, user, "model_released", version)
    db.commit()
    return model_card(version, db)


def approved_release(db, entry, payload, requester, approver, _background):
    """A second HR person approved the release: it happens now, in the name of the person who asked."""
    note = f"{payload['note'].strip()} (approved by {approver.full_name})"
    release_errors(lambda: registry.release(db, entry.subject, requester, note))
    record(db, approver, "model_released", entry.subject)
    return {"version": entry.subject}


approvals.register("model_release", approved_release)


# ─── Live fairness ────────────────────────────────────────────────────────────
class GroupOut(BaseModel):
    group: str
    count: int | None
    rate: float | None
    shown: bool


class StageOut(BaseModel):
    stage: str
    groups: list[GroupOut]
    ratio: float | None
    p_value: float | None = Field(description="chance of a gap this big if the groups really were alike (when below 0.8)")
    status: str = Field(description="passes, below four-fifths, within chance, or not enough data")


class CharacteristicOut(BaseModel):
    characteristic: str
    label: str
    stages: list[StageOut]


class FairnessOut(BaseModel):
    rule: str
    min_group: int
    employees: int
    with_monitoring_data: int
    model_version: str | None
    overall: str
    checks: list[CharacteristicOut]


@router.get("/fairness", response_model=FairnessOut)
def live_fairness(cycle_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(readers)):
    """
    The four-fifths rule on today's directory and decisions: the model, managers' nominations and HR's approvals.
    With `cycle_id`: on that review cycle's saved scores, and the nominations and decisions made in it.
    """
    cycle = None
    if cycle_id is not None:
        cycle = db.get(ReviewCycle, cycle_id)
        if cycle is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such review cycle.")
    return monitoring.report(db, cycle)


# ─── Audit trail ──────────────────────────────────────────────────────────────
class AuditEventOut(BaseModel):
    id: int
    at: str
    event: str
    label: str
    actor: str
    subject_type: str
    subject_id: str
    model_version: str | None
    payload: dict[str, Any]
    hash: str


class AuditPageOut(BaseModel):
    events: list[AuditEventOut]
    total: int
    page: int
    pages: int
    event_types: dict[str, str]


class VerifyOut(BaseModel):
    intact: bool
    events: int
    first_broken_id: int | None
    problem: str | None


PAGE_SIZE = 50
auditors = require_roles(AUDITOR, ADMIN)


@router.get("/audit", response_model=AuditPageOut)
def audit_trail(event: str | None = None, subject_type: str | None = None, subject_id: str | None = None,
                page: int = 1, db: Session = Depends(get_db), _: User = Depends(auditors)):
    """The audit trail, newest first, 50 per page; filter by event, or by what it is about."""
    query = select(audit.AuditEvent)
    if event:
        query = query.where(audit.AuditEvent.event == event)
    if subject_type:
        query = query.where(audit.AuditEvent.subject_type == subject_type)
    if subject_id:
        query = query.where(audit.AuditEvent.subject_id == subject_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(max(page, 1), pages)
    rows = db.scalars(query.order_by(audit.AuditEvent.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    return {"events": [audit.describe(e) for e in rows], "total": total, "page": page, "pages": pages,
            "event_types": audit.EVENTS}


@router.get("/audit/verify", response_model=VerifyOut)
def verify_trail(db: Session = Depends(get_db), _: User = Depends(auditors)):
    """Recompute every hash: is the trail exactly as it was written?"""
    return audit.verify(db)
