"""
The user study, run inside the app (docs/USER_TEST.md).

- The admin creates a session: the participant gets a code (P1, P2, ...) and the facilitator a private link.
- The facilitator opens the link in a second window: consent, each task timed with its outcome (yes, with a hint,
  or no) and notes, then the participant answers the questionnaire. The link needs no sign-in, so the participant
  can sign in and out as employee, manager and HR in the main window; it only works for its own session, and stops
  working once the session is finished.
- The admin saves every finished session to backend/evaluation/user_test_sus.csv and user_test_tasks.csv (the
  formats evaluation/user_test.py reads), runs the analysis, and reads results/user_test.md on the same page.
Nothing here identifies a participant, and nothing here reaches the promotion code or the model.
"""
import csv
import hashlib
import io
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.activity import record
from app.core.database import get_db
from app.core.roles import ADMIN
from app.core.security import require_roles
from app.study.models import StudyAnswer, StudySession, StudyTask
from app.study.protocol import CONSENT, ITEMS, SECTIONS, TASKS

router = APIRouter(prefix="/api/study", tags=["user study"])
admin_only = require_roles(ADMIN)
EVALUATION = Path(__file__).resolve().parents[2] / "evaluation"
SUS_COLUMNS = ["participant", "role_played", *ITEMS, "comments"]
TASK_COLUMNS = ["participant", "task", "completed", "seconds", "notes"]


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def summary(db: Session, s: StudySession) -> dict:
    tasks = db.scalar(select(func.count()).select_from(StudyTask).where(StudyTask.session_id == s.id))
    answers = db.scalar(select(func.count()).select_from(StudyAnswer).where(StudyAnswer.session_id == s.id))
    return {"id": s.id, "code": s.code, "created_at": s.created_at.isoformat(timespec="minutes"),
            "consented": s.consent_at is not None, "tasks_done": tasks, "tasks": len(TASKS),
            "answers": answers, "items": len(ITEMS), "finished": s.finished_at is not None}


# ─── The admin ────────────────────────────────────────────────────────────────
@router.get("/sessions")
def sessions(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [summary(db, s) for s in db.scalars(select(StudySession).order_by(StudySession.id.desc()))]


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def new_session(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """A new participant: their code, and the facilitator's link (shown once; only its hash is kept)."""
    number = (db.scalar(select(func.count()).select_from(StudySession)) or 0) + 1
    while db.scalar(select(StudySession).where(StudySession.code == f"P{number}")):
        number += 1
    token = secrets.token_urlsafe(24)
    entry = StudySession(code=f"P{number}", token_hash=digest(token))
    db.add(entry)
    record(db, user, "study_session_created", entry.code)
    db.commit()
    return {**summary(db, entry), "link": f"/study/{token}"}


def rows(db: Session) -> tuple[list[dict], list[dict]]:
    """Every finished session, as the two CSV files' rows."""
    sus, tasks = [], []
    for s in db.scalars(select(StudySession).where(StudySession.finished_at.is_not(None)).order_by(StudySession.id)):
        answers = {a.item: a.value for a in db.scalars(select(StudyAnswer).where(StudyAnswer.session_id == s.id))}
        sus.append({"participant": s.code, "role_played": s.roles_played or "", **{k: answers.get(k, "") for k in ITEMS},
                    "comments": s.comments or ""})
        for t in db.scalars(select(StudyTask).where(StudyTask.session_id == s.id).order_by(StudyTask.id)):
            tasks.append({"participant": s.code, "task": t.task, "completed": t.completed, "seconds": t.seconds,
                          "notes": t.notes or ""})
    return sus, tasks


def write_csv(path: Path, columns: list[str], data: list[dict]) -> None:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    writer.writerows(data)
    path.write_text(out.getvalue(), encoding="utf-8")


@router.post("/analyse")
def analyse(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """
    Save every finished session to the evaluation files (replacing them) and run evaluation/user_test.py. Returns the
    report it writes (results/user_test.md).
    """
    from evaluation import user_test

    sus, tasks = rows(db)
    if not sus:
        raise HTTPException(status.HTTP_409_CONFLICT, "No finished sessions yet.")
    write_csv(EVALUATION / "user_test_sus.csv", SUS_COLUMNS, sus)
    write_csv(EVALUATION / "user_test_tasks.csv", TASK_COLUMNS, tasks)
    user_test.main()
    report = user_test.RESULTS / "user_test.md"
    record(db, user, "study_analysed", f"{len(sus)} participants")
    db.commit()
    return {"participants": len(sus), "report": report.read_text(encoding="utf-8") if report.exists() else ""}


# ─── The facilitator's link ───────────────────────────────────────────────────
def by_token(db: Session, token: str) -> StudySession:
    session = db.scalar(select(StudySession).where(StudySession.token_hash == digest(token)))
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This study link isn't valid.")
    return session


def open_session(db: Session, token: str) -> StudySession:
    session = by_token(db, token)
    if session.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This session is finished. Thank you!")
    return session


@router.get("/run/{token}")
def protocol(token: str, db: Session = Depends(get_db)):
    """The session's code, what's done so far, and the protocol: consent, tasks and questionnaire."""
    s = by_token(db, token)
    done = {t.task: {"completed": t.completed, "seconds": t.seconds, "notes": t.notes}
            for t in db.scalars(select(StudyTask).where(StudyTask.session_id == s.id))}
    return {"code": s.code, "consented": s.consent_at is not None, "finished": s.finished_at is not None,
            "consent": CONSENT, "done": done,
            "tasks": [{"task": t, "role": role, "text": text, "scenario": scenario} for t, role, text, scenario in TASKS],
            "sections": [{"title": title, "items": [{"key": k, "text": v} for k, v in items.items()]} for title, items in SECTIONS]}


@router.post("/run/{token}/consent")
def consent(token: str, db: Session = Depends(get_db)):
    s = open_session(db, token)
    s.consent_at = s.consent_at or datetime.now(timezone.utc)
    db.commit()
    return {"consented": True}


class TaskIn(BaseModel):
    task: str = Field(pattern=r"^T(1[01]|[1-9])$")
    completed: str = Field(pattern="^(yes|help|no)$")
    seconds: int = Field(ge=0, le=3600)
    notes: str | None = Field(default=None, max_length=500)


@router.post("/run/{token}/tasks")
def save_task(token: str, body: TaskIn, db: Session = Depends(get_db)):
    """One task's outcome and time (saving it again replaces it)."""
    s = open_session(db, token)
    if s.consent_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Record the participant's consent first.")
    entry = db.scalar(select(StudyTask).where(StudyTask.session_id == s.id, StudyTask.task == body.task))
    if entry is None:
        entry = StudyTask(session_id=s.id, task=body.task, completed=body.completed, seconds=body.seconds)
        db.add(entry)
    entry.completed, entry.seconds, entry.notes = body.completed, body.seconds, (body.notes or "").strip() or None
    db.commit()
    return {"saved": body.task}


class FinishIn(BaseModel):
    answers: dict[str, int]
    roles_played: str = Field(min_length=2, max_length=80)
    comments: str | None = Field(default=None, max_length=2000)


@router.post("/run/{token}/finish")
def finish(token: str, body: FinishIn, db: Session = Depends(get_db)):
    """The participant's questionnaire. Every statement needs an answer from 1 to 5; then the link stops working."""
    s = open_session(db, token)
    if s.consent_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Record the participant's consent first.")
    missing = [k for k in ITEMS if k not in body.answers]
    if missing or any(v not in (1, 2, 3, 4, 5) for v in body.answers.values()) or set(body.answers) - set(ITEMS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please answer every statement from 1 to 5.")
    for key in ITEMS:
        db.add(StudyAnswer(session_id=s.id, item=key, value=body.answers[key]))
    s.roles_played, s.comments = body.roles_played.strip(), (body.comments or "").strip() or None
    s.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"finished": True, "code": s.code}
