"""
Teams API: HR owns reporting lines (who manages whom); managers and HR arrange cover while a manager is away.

- GET  /api/promotion/teams                HR: every manager with their team, who they report to and any cover; and
                                           everyone without a manager, so nobody falls through the gaps
- PUT  /api/promotion/teams/assign         HR: put employees under a manager (or under nobody)
- GET  /api/promotion/teams/managers       HR, managers: the active managers' names (to choose who covers)
- GET  /api/promotion/teams/covers         HR, managers: the covers now and coming up (a manager sees their own)
- POST /api/promotion/teams/covers         a manager (for their own team) or HR: arrange cover
- POST /api/promotion/teams/covers/{id}/end  the same people: end a cover early
The admin's team editor (routes_admin.py) still works, for setting up a new manager's account.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import notify_new_team_members
from app.accounts.models import User
from app.core import audit
from app.core.activity import record
from app.core.database import get_promotion_db as get_db  # the promotion code's own (restricted) connection
from app.core.roles import HR, MANAGER
from app.core.security import require_roles
from app.promotion import teams
from app.promotion.models import Employee, TeamCover, current_employees

router = APIRouter(prefix="/api/promotion/teams", tags=["teams"])


def managers(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == MANAGER, User.is_active.is_(True)).order_by(User.full_name)))


def cover_out(db: Session, cover: TeamCover) -> dict:
    today = date.today()
    return {"id": cover.id, "manager_user_id": cover.manager_user_id, "manager": db.get(User, cover.manager_user_id).full_name,
            "cover_user_id": cover.cover_user_id, "cover": db.get(User, cover.cover_user_id).full_name,
            "starts": cover.starts.isoformat(), "ends": cover.ends.isoformat(), "note": cover.note, "set_by": cover.set_by_name,
            "status": "ended" if cover.ended_at else "active" if cover.starts <= today <= cover.ends else "upcoming" if cover.starts > today else "ended"}


@router.get("")
def overview(_: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """Every manager (with who they report to, their team and any cover today), and everyone without a manager."""
    rows = []
    for manager in managers(db):
        above = teams.chain_above(db, manager.id)
        branch = teams.team_of(db, manager)
        cover = teams.cover_for(db, manager.id)
        rows.append({
            "user_id": manager.id, "full_name": manager.full_name, "job_title": manager.job_title,
            "employee_id": manager.employee_id,
            "reports_to": db.get(User, above[0]).full_name if above else None,
            "level": len(above),
            "direct": sum(1 for r in branch.values() if r == teams.DIRECT),
            "branch": sum(1 for r in branch.values() if r == teams.BRANCH),
            "team": [{"id": e.id, "full_name": e.full_name, "department": e.department}
                     for e in db.scalars(current_employees().where(Employee.manager_user_id == manager.id).order_by(Employee.full_name))],
            "cover": cover_out(db, cover) if cover else None,
        })
    # Top of each reporting line first, then the managers under them, as an org chart reads
    order = {r["user_id"]: r for r in rows}
    def path(row):
        chain = list(reversed(teams.chain_above(db, row["user_id"])))
        return [order[m]["full_name"] if m in order else "" for m in chain] + [row["full_name"]]
    rows.sort(key=path)
    unassigned = [{"id": e.id, "full_name": e.full_name, "department": e.department}
                  for e in db.scalars(current_employees().where(Employee.manager_user_id.is_(None)).order_by(Employee.department, Employee.full_name))]
    total = len(db.scalars(current_employees()).all())
    return {"managers": rows, "unassigned": unassigned, "employees": total}


class AssignIn(BaseModel):
    employee_ids: list[int] = Field(min_length=1, max_length=5000)
    manager_user_id: int | None = None  # None: take them off their manager's team
    reason: str | None = Field(default=None, max_length=500)


@router.put("/assign")
def assign(body: AssignIn, background: BackgroundTasks, user: User = Depends(require_roles(HR)), db: Session = Depends(get_db)):
    """HR puts these employees under a manager (moving them from any other team), or under nobody."""
    manager = None
    if body.manager_user_id is not None:
        manager = db.get(User, body.manager_user_id)
        if manager is None or manager.role != MANAGER or not manager.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "People can only be put under an active manager account.")
    people = list(db.scalars(select(Employee).where(Employee.id.in_(body.employee_ids))))
    if missing := set(body.employee_ids) - {e.id for e in people}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No employee with number(s): {', '.join(map(str, sorted(missing)))}.")
    if manager is not None:
        loops = [e.full_name for e in people if teams.would_loop(db, e, manager.id)]
        if loops:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"{', '.join(loops)} can't report to {manager.full_name}: {manager.full_name} already reports "
                                "to them, so the reporting line would go round in a circle.")
    moved = [e for e in people if e.manager_user_id != (manager.id if manager else None)]
    for employee in moved:
        audit.append(db, "team_changed", user, "employee", employee.id,
                     {"from_manager": employee.manager_user_id, "to_manager": manager.id if manager else None,
                      "reason": (body.reason or "").strip() or None})
        employee.manager_user_id = manager.id if manager else None
    record(db, user, "team_assigned", f"{len(moved)} to {manager.full_name if manager else 'no manager'}")
    db.commit()
    if manager is not None and moved:
        notify_new_team_members(background, db, {manager.id: sorted(e.full_name for e in moved)})
    return {"moved": len(moved)}


@router.get("/managers")
def list_managers(_: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """The active managers' names, to choose who covers (names only)."""
    return [{"user_id": m.id, "full_name": m.full_name} for m in managers(db)]


@router.get("/covers")
def list_covers(user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """Covers now and coming up. A manager sees the ones they give or receive; HR sees all."""
    query = select(TeamCover).where(TeamCover.ended_at.is_(None), TeamCover.ends >= date.today()).order_by(TeamCover.starts)
    if user.role == MANAGER:
        query = query.where((TeamCover.manager_user_id == user.id) | (TeamCover.cover_user_id == user.id))
    return [cover_out(db, c) for c in db.scalars(query)]


class CoverIn(BaseModel):
    manager_user_id: int | None = None  # HR names the manager who is away; a manager arranges cover for themselves
    cover_user_id: int
    starts: date
    ends: date
    note: str | None = Field(default=None, max_length=500)


@router.post("/covers", status_code=status.HTTP_201_CREATED)
def arrange_cover(body: CoverIn, user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """While a manager is away, another manager sees and may nominate their team. At most 6 months; no overlaps."""
    away_id = user.id if user.role == MANAGER else body.manager_user_id
    if user.role == MANAGER and body.manager_user_id not in (None, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Managers arrange cover for their own team only.")
    away, cover = db.get(User, away_id) if away_id else None, db.get(User, body.cover_user_id)
    for who in (away, cover):
        if who is None or who.role != MANAGER or not who.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cover is between two active manager accounts.")
    if away.id == cover.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A manager can't cover for themselves.")
    if not date.today() <= body.starts <= body.ends <= body.starts + timedelta(days=183):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Cover starts today or later, and lasts at most six months.")
    overlapping = db.scalar(select(TeamCover).where(TeamCover.manager_user_id == away.id, TeamCover.ended_at.is_(None),
                                                   TeamCover.starts <= body.ends, TeamCover.ends >= body.starts))
    if overlapping is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{away.full_name} already has cover from {overlapping.starts} to {overlapping.ends}.")
    entry = TeamCover(manager_user_id=away.id, cover_user_id=cover.id, starts=body.starts, ends=body.ends,
                      note=(body.note or "").strip() or None, set_by_name=user.full_name)
    db.add(entry)
    db.flush()
    audit.append(db, "cover_arranged", user, "cover", entry.id, {"manager": away.id, "cover": cover.id,
                                                                  "starts": body.starts.isoformat(), "ends": body.ends.isoformat()})
    record(db, user, "cover_arranged", f"{cover.full_name} covers {away.full_name}, {body.starts} to {body.ends}")
    db.commit()
    return cover_out(db, entry)


@router.post("/covers/{cover_id}/end")
def end_cover(cover_id: int, user: User = Depends(require_roles(HR, MANAGER)), db: Session = Depends(get_db)):
    """End a cover early (or cancel one that hasn't started): the manager who is away, the cover, or HR."""
    cover = db.get(TeamCover, cover_id)
    if cover is None or (user.role == MANAGER and user.id not in (cover.manager_user_id, cover.cover_user_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such cover.")
    if cover.ended_at is None:
        cover.ended_at = datetime.now(timezone.utc)
        audit.append(db, "cover_ended", user, "cover", cover.id, {})
        record(db, user, "cover_ended", f"{db.get(User, cover.cover_user_id).full_name} for {db.get(User, cover.manager_user_id).full_name}")
        db.commit()
    return cover_out(db, cover)
