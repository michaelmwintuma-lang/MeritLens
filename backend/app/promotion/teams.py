"""
Teams and reporting lines: who manages whom, and who may see and nominate whom.

Every employee has at most one manager (Employee.manager_user_id, a manager's account). A manager's account can be
linked to their own employee record, and that record has a manager too, so reporting lines chain upwards: a head of
department's branch is everyone below them. From that:

- direct:  a manager's own team. They see them and may recommend them for promotion.
- cover:   the team of a manager who is away, while this manager covers for them (TeamCover). Seen and nominated
           exactly like a direct team, for those days only.
- branch:  everyone further down the reporting line. Seen read-only (a skip-level view): only their own manager
           recommends them, so every recommendation has one accountable person.

HR owns the reporting lines (routes_teams.py); a reporting line can never loop back on itself.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.roles import MANAGER
from app.promotion.models import Employee, TeamCover

DIRECT, COVER, BRANCH = "direct", "cover", "branch"
MAY_NOMINATE = (DIRECT, COVER)


def direct_reports(db: Session, manager_id: int) -> list[int]:
    return list(db.scalars(select(Employee.id).where(Employee.manager_user_id == manager_id)))


def active_covers(db: Session, today: date | None = None):
    """The covers in force today."""
    today = today or date.today()
    return db.scalars(select(TeamCover).where(TeamCover.ended_at.is_(None), TeamCover.starts <= today, TeamCover.ends >= today))


def covering_for(db: Session, user: User, today: date | None = None) -> list[TeamCover]:
    """The covers this manager is giving today (for managers who are away)."""
    return [c for c in active_covers(db, today) if c.cover_user_id == user.id]


def manager_login_for(db: Session, employee_id: int) -> User | None:
    """The manager account linked to this employee record, if they are a manager."""
    return db.scalar(select(User).where(User.employee_id == employee_id, User.role == MANAGER))


def team_of(db: Session, user: User, today: date | None = None) -> dict[int, str]:
    """Everyone this manager may see: {employee id: "direct" | "cover" | "branch"}."""
    found = {e: DIRECT for e in direct_reports(db, user.id)}
    for cover in covering_for(db, user, today):
        for e in direct_reports(db, cover.manager_user_id):
            found.setdefault(e, COVER)
    # Down the reporting line: managers whose own record reports to this user, then theirs, and so on
    seen, frontier = {user.id}, [user.id]
    while frontier:
        reports = direct_reports(db, frontier.pop())
        for manager in db.scalars(select(User).where(User.employee_id.in_(reports), User.role == MANAGER)):
            if manager.id in seen:
                continue
            seen.add(manager.id)
            frontier.append(manager.id)
            for e in direct_reports(db, manager.id):
                found.setdefault(e, BRANCH)
    found.pop(user.employee_id, None)  # a manager's own record is never part of their team
    return found


def chain_above(db: Session, manager_id: int) -> list[int]:
    """The manager accounts above this one, nearest first (their manager, that manager's manager, ...)."""
    chain, current = [], db.get(User, manager_id)
    while current is not None and current.employee_id:
        record = db.get(Employee, current.employee_id)
        if record is None or record.manager_user_id is None or record.manager_user_id in chain or record.manager_user_id == manager_id:
            break
        chain.append(record.manager_user_id)
        current = db.get(User, record.manager_user_id)
    return chain


def would_loop(db: Session, employee: Employee, manager_id: int) -> bool:
    """Whether putting this employee under this manager makes a reporting line loop back on itself."""
    their_login = manager_login_for(db, employee.id)
    if their_login is None:
        return False
    return their_login.id == manager_id or their_login.id in chain_above(db, manager_id)


def manager_name(db: Session, employee: Employee) -> str | None:
    if employee.manager_user_id is None:
        return None
    manager = db.get(User, employee.manager_user_id)
    return manager.full_name if manager else None


def cover_for(db: Session, manager_id: int | None, today: date | None = None) -> TeamCover | None:
    """Who covers for this manager today, if anyone."""
    if manager_id is None:
        return None
    return next((c for c in active_covers(db, today) if c.manager_user_id == manager_id), None)
