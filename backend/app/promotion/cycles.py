"""
Review cycles: score everyone once, keep the scores, and run a promotion round against them.

1. HR opens a cycle ("2026 mid-year"), optionally with the last day managers may nominate. The live model scores
   every employee at once, and each score is saved with the exact inputs it came from (CycleScore), so what the
   model said can always be reproduced. Lists then show these scores straight away.
2. During the cycle a score changes only when the employee's record changes: HR edits it or confirms a record
   correction. That change is in the record's history, and the cycle keeps the score at opening beside the new one.
   Everyone in a cycle is scored by the same model: a new model can't be released while a cycle is open
   (app/governance/registry.py).
3. Nominations and decisions made while the cycle is open belong to it. After the nomination deadline, managers
   can't nominate in that cycle any more.
4. HR closes the cycle once every nomination in it has been decided. Closed cycles stay as they are: each
   employee's scores over the cycles show how their readiness has moved.

No cycle open: everything works as before, scored on demand and not saved.
"""
import json
from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import audit
from app.core.holds import active_hold
from app.promotion.models import CycleScore, Decision, Employee, Nomination, ReviewCycle, current_employees

# How many people "biggest movers since the last cycle" lists each way
MOVERS = 5


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | date | None) -> str | None:
    if moment is None:
        return None
    return moment.isoformat(timespec="seconds") if isinstance(moment, datetime) else moment.isoformat()


def open_cycle(db: Session) -> ReviewCycle | None:
    """The cycle that is open now, if any (there is never more than one)."""
    return db.scalar(select(ReviewCycle).where(ReviewCycle.status == "open"))


def nominations_open(cycle: ReviewCycle | None, today: date | None = None) -> bool:
    """Whether managers may still nominate in this cycle (always, without a deadline)."""
    return cycle is None or cycle.nominations_close is None or (today or date.today()) <= cycle.nominations_close


def summary(cycle: ReviewCycle) -> dict:
    """The cycle itself, as every page shows it."""
    days_left = (cycle.nominations_close - date.today()).days if cycle.nominations_close and cycle.status == "open" else None
    return {"id": cycle.id, "name": cycle.name, "status": cycle.status, "model_version": cycle.model_version,
            "threshold": cycle.threshold, "nominations_close": iso(cycle.nominations_close),
            "nominations_open": cycle.status == "open" and nominations_open(cycle), "days_left": days_left,
            "note": cycle.note, "opened_by": cycle.opened_by_name, "opened_at": iso(cycle.opened_at),
            "closed_by": cycle.closed_by_name, "closed_at": iso(cycle.closed_at)}


# ─── Opening, and scores within an open cycle ─────────────────────────────────
def open_new(db: Session, live, user, name: str, nominations_close: date | None, note: str | None) -> ReviewCycle:
    """Open a cycle and save every employee's score with the live model. The caller commits."""
    cycle = ReviewCycle(name=name, model_version=live.version, threshold=live.threshold,
                        nominations_close=nominations_close, note=note, opened_by_name=user.full_name)
    db.add(cycle)
    db.flush()  # gives the cycle its id
    employees = list(db.scalars(current_employees().order_by(Employee.id)))
    for employee, score in zip(employees, live.scores([e.record for e in employees])):
        db.add(CycleScore(cycle_id=cycle.id, employee_id=employee.id, score=round(score, 4),
                          recommended=score >= live.threshold, record_json=json.dumps(employee.record, sort_keys=True),
                          score_at_opening=round(score, 4)))
    db.flush()
    recommended = sum(1 for s in scores_of(db, cycle) if s.recommended)
    audit.append(db, "cycle_opened", user, "cycle", cycle.id, {
        "name": name, "people": len(employees), "recommended": recommended, "threshold": live.threshold,
        "nominations_close": iso(nominations_close)}, model_version=live.version)
    return cycle


def scores_of(db: Session, cycle: ReviewCycle) -> list[CycleScore]:
    return list(db.scalars(select(CycleScore).where(CycleScore.cycle_id == cycle.id)))


def scores_for(db: Session, cycle: ReviewCycle, employees: list[Employee], live) -> dict[int, CycleScore]:
    """
    The saved scores of these employees in an open cycle. Someone added to the directory after the cycle opened
    is scored now (with the same model) and added, so the cycle always covers everyone.
    """
    saved = {s.employee_id: s for s in db.scalars(select(CycleScore).where(
        CycleScore.cycle_id == cycle.id, CycleScore.employee_id.in_([e.id for e in employees])))}
    missing = [e for e in employees if e.id not in saved]
    if missing and cycle.status == "open":
        for employee, score in zip(missing, live.scores([e.record for e in missing])):
            saved[employee.id] = CycleScore(cycle_id=cycle.id, employee_id=employee.id, score=round(score, 4),
                                            recommended=score >= cycle.threshold,
                                            record_json=json.dumps(employee.record, sort_keys=True))
            db.add(saved[employee.id])
        db.commit()
    return saved


def rescore(db: Session, employee: Employee, new_record: dict, new_score: float, record_change_id: int) -> CycleScore | None:
    """
    An employee's record changed while a cycle is open: their saved score follows, linked to the record change
    (which is in the record's history and the audit trail). The caller commits.
    """
    cycle = open_cycle(db)
    if cycle is None:
        return None
    entry = db.scalar(select(CycleScore).where(CycleScore.cycle_id == cycle.id, CycleScore.employee_id == employee.id))
    if entry is None:
        return None
    entry.score, entry.recommended = round(new_score, 4), new_score >= cycle.threshold
    entry.record_json = json.dumps({**new_record, "department": employee.department}, sort_keys=True)
    entry.scored_at, entry.record_change_id = now(), record_change_id
    return entry


# ─── How a cycle is going ─────────────────────────────────────────────────────
def progress(db: Session, cycle: ReviewCycle, with_people: bool) -> dict:
    """
    Everything the cycle page shows: totals, the nomination pipeline, each department, who the model recommends but
    nobody has nominated, and the movement since the previous cycle. `with_people` False (the auditor) leaves out
    every list of named people and keeps only totals.
    """
    scores = scores_of(db, cycle)
    employees = {e.id: e for e in db.scalars(select(Employee).where(Employee.id.in_([s.employee_id for s in scores])))}
    nominations = list(db.scalars(select(Nomination).where(Nomination.cycle_id == cycle.id)))
    decisions = {d.nomination_id: d for d in db.scalars(select(Decision).where(Decision.cycle_id == cycle.id))}
    held = sum(1 for n in nominations if n.status == "pending" and active_hold(db, n.id) is not None)
    nominated = {n.employee_id for n in nominations}
    approved = {d.employee_id for d in decisions.values() if d.decision == "approve"}
    status_counts = Counter(n.status for n in nominations)

    departments: dict[str, Counter] = {}
    for s in scores:
        employee = employees.get(s.employee_id)
        if employee is None:
            continue
        row = departments.setdefault(employee.department, Counter())
        row["people"] += 1
        row["recommended"] += s.recommended
        row["nominated"] += s.employee_id in nominated
        row["approved"] += s.employee_id in approved

    totals = {
        "people": len(scores),
        "recommended": sum(1 for s in scores if s.recommended),
        "nominated": len(nominated),
        "waiting": status_counts["pending"] - held,
        "on_hold": held,
        "approved": status_counts["approved"],
        "rejected": status_counts["rejected"],
        "against_model": sum(1 for d in decisions.values() if not d.agrees_with_model),
        "rescored": sum(1 for s in scores if s.record_change_id is not None),
        "added_late": sum(1 for s in scores if s.score_at_opening is None),
    }
    not_nominated = [s for s in scores if s.recommended and s.employee_id not in nominated]
    totals["recommended_not_nominated"] = len(not_nominated)
    # Recommended, but with nobody to recommend them: HR should give them a manager (Teams)
    totals["recommended_no_manager"] = sum(1 for s in not_nominated
                                           if s.employee_id in employees and employees[s.employee_id].manager_user_id is None)
    pending = status_counts["pending"]
    result = {
        "cycle": summary(cycle),
        "totals": totals,
        "by_department": [{"department": d, **dict(c)} for d, c in sorted(departments.items())],
        "movement": movement(db, cycle, scores, employees, with_people),
        "can_close": cycle.status == "open" and pending == 0,
        "close_blocker": (f"{pending} nomination{'' if pending == 1 else 's'} in this cycle {'is' if pending == 1 else 'are'} "
                          "still waiting for a decision.") if cycle.status == "open" and pending else None,
    }
    if with_people:
        managers = {u.id: u.full_name for u in db.scalars(select(User).where(
            User.id.in_({e.manager_user_id for e in employees.values() if e.manager_user_id})))}
        result["not_nominated"] = sorted(
            ({"employee_id": s.employee_id, "full_name": employees[s.employee_id].full_name,
              "department": employees[s.employee_id].department, "score": s.score,
              "manager": managers.get(employees[s.employee_id].manager_user_id)}
             for s in not_nominated if s.employee_id in employees), key=lambda r: -r["score"])
    return result


def previous_cycle(db: Session, cycle: ReviewCycle) -> ReviewCycle | None:
    return db.scalar(select(ReviewCycle).where(ReviewCycle.id < cycle.id).order_by(ReviewCycle.id.desc()).limit(1))


def movement(db: Session, cycle: ReviewCycle, scores: list[CycleScore], employees: dict, with_people: bool) -> dict:
    """How scores moved since the previous cycle, for the people in both: who crossed the threshold, and how far."""
    before = previous_cycle(db, cycle)
    if before is None:
        return {"previous": None}
    earlier = {s.employee_id: s for s in scores_of(db, before)}
    pairs = [(s, earlier[s.employee_id]) for s in scores if s.employee_id in earlier and s.employee_id in employees]
    changes = sorted(((s.score - e.score, s, e) for s, e in pairs), key=lambda c: c[0])
    result = {
        "previous": {"id": before.id, "name": before.name},
        "compared": len(pairs),
        "crossed_up": sum(1 for s, e in pairs if s.recommended and not e.recommended),
        "crossed_down": sum(1 for s, e in pairs if e.recommended and not s.recommended),
        "average_change": round(sum(c[0] for c in changes) / len(changes), 4) if changes else None,
    }
    if with_people:
        person = lambda change, s, e: {"employee_id": s.employee_id, "full_name": employees[s.employee_id].full_name,  # noqa: E731
                                       "department": employees[s.employee_id].department, "before": e.score,
                                       "now": s.score, "change": round(change, 4)}
        result["risers"] = [person(*c) for c in reversed(changes[-MOVERS:]) if c[0] > 0]
        result["fallers"] = [person(*c) for c in changes[:MOVERS] if c[0] < 0]
    return result


def close(db: Session, cycle: ReviewCycle, user) -> None:
    """Close an open cycle whose nominations are all decided. The caller commits."""
    report = progress(db, cycle, with_people=False)
    if not report["can_close"]:
        raise ValueError(report["close_blocker"] or "This cycle is already closed.")
    cycle.status, cycle.closed_at, cycle.closed_by_name = "closed", now(), user.full_name
    audit.append(db, "cycle_closed", user, "cycle", cycle.id, {"name": cycle.name, **report["totals"]},
                 model_version=cycle.model_version)


def trend(db: Session, employee_id: int) -> list[dict]:
    """One employee's saved score in every cycle, oldest first."""
    rows = db.execute(select(CycleScore, ReviewCycle).join(ReviewCycle, ReviewCycle.id == CycleScore.cycle_id)
                      .where(CycleScore.employee_id == employee_id).order_by(ReviewCycle.id))
    return [{"cycle_id": c.id, "name": c.name, "status": c.status, "opened_at": iso(c.opened_at),
             "score": s.score, "threshold": c.threshold, "recommended": s.recommended,
             "score_at_opening": s.score_at_opening, "rescored": s.record_change_id is not None}
            for s, c in rows]
