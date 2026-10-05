"""
Evidence for anonymous reports: photos and videos.

The reporter adds files with their case ID and key, exactly like opening the case, so a file is linked to the
case and never to the reporter's account. Each file's hidden details (location, device, owner, time) are removed
before it is saved (app/reporting/evidence.py). The reporter can see and remove their own files while the case is
open; HR can view them, but not delete them.

Files are never served directly from a folder: only through these endpoints, to the reporter with their key or to
HR, and never cached by the browser.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.database import get_db
from app.core.roles import HR
from app.core.security import require_roles
from app.reporting import evidence
from app.reporting.models import Evidence, Report
from app.reporting.routes import AccessIn, open_case, reporters, today

router = APIRouter(prefix="/api/reports/evidence", tags=["reporting"])
hr_router = APIRouter(prefix="/api/hr/reports", tags=["reporting (HR)"])
hr_only = require_roles(HR)
CHUNK = 1024 * 1024


def send_file(item: Evidence, case_id: str) -> FileResponse:
    ext = item.stored_name.rsplit(".", 1)[-1]
    return FileResponse(evidence.path_of(item), media_type=item.content_type, headers={
        "Content-Disposition": f'inline; filename="{case_id}-evidence-{item.number}.{ext}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


def find(db: Session, case_id: str, evidence_id: str) -> Evidence:
    item = db.get(Evidence, evidence_id)
    if item is None or item.case_id != case_id or not evidence.path_of(item).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such file in this case.")
    return item


# ─── The reporter ─────────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def upload(case_id: str = Form(...), key: str = Form(...), keep_sound: bool = Form(True),
           file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(reporters)):
    """Add one photo or video to the case, after removing its hidden details. Returns the case's evidence list."""
    report = open_case(case_id, key, db)
    if report.status == "closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This case is closed.")
    if len(evidence.listing(db, report.case_id)) >= evidence.MAX_FILES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A case can have up to {evidence.MAX_FILES} files.")

    head = file.file.read(16)
    kind = evidence.kind_of(head)
    if kind is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Only photos (JPEG, PNG, WebP) and videos (MP4, MOV, WebM) can be added.")
    limit = evidence.MAX_PHOTO_BYTES if kind == "photo" else evidence.MAX_VIDEO_BYTES
    # Copy the upload to a private temporary file, stopping as soon as it's too big
    source = evidence.temporary_file()
    try:
        size = 0
        with source.open("wb") as out:
            chunk = head
            while chunk:
                size += len(chunk)
                if size > limit:
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                                        f"{'Photos' if kind == 'photo' else 'Videos'} can be up to {limit // (1024 * 1024)} MB.")
                out.write(chunk)
                chunk = file.file.read(CHUNK)
        try:
            if kind == "photo":
                data, content_type, ext = evidence.clean_photo(source.read_bytes())
                evidence.store(db, report.case_id, kind, content_type, ext, data=data, today=today())
            else:
                cleaned, content_type, ext = evidence.clean_video(source, head, keep_sound=keep_sound)
                evidence.store(db, report.case_id, kind, content_type, ext, move_from=cleaned, today=today())
        except evidence.NotUsable as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
        except evidence.VideoUnavailable as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    finally:
        source.unlink(missing_ok=True)  # the original, with its hidden details, is never kept
    db.commit()
    return {"evidence": evidence.listing(db, report.case_id)}


@router.post("/{evidence_id}/view")
def reporter_view(evidence_id: str, body: AccessIn, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """The reporter sees one of their files (the cleaned version, exactly what HR sees)."""
    report = open_case(body.case_id, body.key, db)
    return send_file(find(db, report.case_id, evidence_id), report.case_id)


@router.post("/{evidence_id}/remove")
def reporter_remove(evidence_id: str, body: AccessIn, db: Session = Depends(get_db), _: User = Depends(reporters)):
    """The reporter removes a file they added, for example if they realise it could identify them."""
    report: Report = open_case(body.case_id, body.key, db)
    if report.status == "closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This case is closed.")
    item = find(db, report.case_id, evidence_id)
    evidence.path_of(item).unlink(missing_ok=True)
    db.delete(item)
    db.commit()
    return {"evidence": evidence.listing(db, report.case_id)}


# ─── HR ───────────────────────────────────────────────────────────────────────
@hr_router.get("/{case_id}/evidence/{evidence_id}")
def hr_view(case_id: str, evidence_id: str, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """HR sees one file attached to a case."""
    return send_file(find(db, case_id, evidence_id), case_id)
