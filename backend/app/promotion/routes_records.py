"""
Employee records API, for HR only: add one employee, edit a record, or import many from a CSV file.

A new employee can be scored straight away: the model only needs their inputs, not retraining. (Retraining is
needed to learn from an organisation's own promotion history; see docs/HOW_IT_WORKS.md.)
"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.contacts import notify_new_team_members
from app.accounts.models import User
from app.core import audit
from app.core.activity import record as log
from app.core.database import get_promotion_db as get_db  # the promotion code's own (restricted) connection
from app.core.roles import AUDITOR, HR, MANAGER
from app.core.security import require_roles
from app.promotion import cycles
from app.promotion.models import Employee, RecordChange
from app.promotion.records import CSV_COLUMNS, GROUPS, field_list, read_csv, to_entry, to_record
from app.promotion.routes import model, warm_explanation

router = APIRouter(prefix="/api/promotion/records", tags=["employee records"])
hr_only = require_roles(HR)


class RecordIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    department: str
    manager_user_id: int | None = None
    values: dict[str, float | str | None]
    reason: str | None = Field(default=None, max_length=1000)  # why the record changed (kept in its history)


class ImportIn(BaseModel):
    csv: str = Field(max_length=2_000_000)
    save: bool = False  # False: only check the file and show what would happen


def departments() -> list[str]:
    """The departments in the training data. Department is not a model input; it only organises who sees whom."""
    return model().info["departments"]


def managers(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == MANAGER, User.is_active).order_by(User.full_name)))


def same_person_exists(db: Session, full_name: str, department: str, ignore_id: int | None = None) -> bool:
    """Someone with this name in this department already: most likely the same person entered twice."""
    query = select(Employee).where(Employee.full_name == full_name, Employee.department == department)
    return any(e.id != ignore_id for e in db.scalars(query))


def check(body: RecordIn, db: Session, ignore_id: int | None = None) -> tuple[dict, dict]:
    """Check one employee's details. Returns (record, warnings), or refuses with every problem listed."""
    record, errors, warnings = to_record(body.values, model().stats)
    if body.department not in departments():
        errors["department"] = f"Department must be one of: {', '.join(departments())}."
    if body.manager_user_id is not None and body.manager_user_id not in {m.id for m in managers(db)}:
        errors["manager_user_id"] = "That manager doesn't exist."
    if same_person_exists(db, body.full_name.strip(), body.department, ignore_id):
        errors["full_name"] = f"{body.full_name.strip()} is already in {body.department}. Edit their record instead."
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {"message": "Please correct the highlighted fields.", "fields": errors})
    return record, warnings


@router.get("/fields")
def fields(db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """Everything the form and the CSV template need: the fields, departments and managers."""
    return {"groups": GROUPS, "fields": field_list(model().stats), "departments": departments(),
            "managers": [{"id": m.id, "full_name": m.full_name, "username": m.username} for m in managers(db)],
            "csv_columns": CSV_COLUMNS}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_employee(body: RecordIn, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """Add one employee to the directory. They can be scored at once, and linked to a login by the admin."""
    record, warnings = check(body, db)
    employee = Employee(full_name=body.full_name.strip(), department=body.department,
                        manager_user_id=body.manager_user_id, record_json=json.dumps(record))
    db.add(employee)
    log(db, user, "employee_added", f"{employee.full_name} ({employee.department})")
    db.commit()
    if employee.manager_user_id:
        notify_new_team_members(background, db, {employee.manager_user_id: [employee.full_name]})
    return {"id": employee.id, "warnings": warnings}


@router.get("/{employee_id}")
def get_record(employee_id: int, db: Session = Depends(get_db), _: User = Depends(hr_only)):
    """One employee's details in the units HR types in, for the edit form."""
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    return {"id": employee.id, "full_name": employee.full_name, "department": employee.department,
            "manager_user_id": employee.manager_user_id, "values": to_entry(json.loads(employee.record_json))}


@router.put("/{employee_id}")
def edit_record(employee_id: int, body: RecordIn, background: BackgroundTasks, db: Session = Depends(get_db),
                user: User = Depends(hr_only)):
    """Update an employee's details, e.g. after a new review. Past decisions keep the score they were made with."""
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    record, warnings = check(body, db, ignore_id=employee_id)
    new_manager = body.manager_user_id if body.manager_user_id != employee.manager_user_id else None
    old_record = json.loads(employee.record_json)
    employee.full_name, employee.department = body.full_name.strip(), body.department
    employee.manager_user_id, employee.record_json = body.manager_user_id, json.dumps(record)
    record_history(db, employee, old_record, record, user, "hr_edit", body.reason)
    log(db, user, "employee_edited", employee.full_name)
    db.commit()
    if new_manager:  # moved to a different manager: tell the new one
        notify_new_team_members(background, db, {new_manager: [employee.full_name]})
    return {"id": employee.id, "warnings": warnings}


def record_history(db: Session, employee: Employee, old: dict, new: dict, user: User, source: str,
                   reason: str | None) -> RecordChange | None:
    """
    Keep a change to the model's inputs in the record's history, with the score before and after. Nothing is
    written when no input changed (a new name or manager doesn't change the score). The caller commits.
    """
    changes = [{"field": f, "old": old.get(f), "new": new[f]} for f in new if old.get(f) != new[f]]
    if not changes:
        return None
    live = model()
    entry = RecordChange(employee_id=employee.id, changed_by=user.id, changed_by_name=user.full_name, source=source,
                         changes_json=json.dumps(changes), reason=(reason or "").strip() or None,
                         score_before=round(live.score(old), 4), score_after=round(live.score(new), 4),
                         model_version=live.version)
    db.add(entry)
    db.flush()  # gives the change its id
    in_cycle = cycles.rescore(db, employee, new, entry.score_after, entry.id)
    audit.append(db, "record_changed", user, "employee", employee.id,
                 {"source": source, "record_change_id": entry.id, "changes": changes,
                  "score_before": entry.score_before, "score_after": entry.score_after,
                  "cycle_id": in_cycle.cycle_id if in_cycle else None}, model_version=live.version)
    warm_explanation(new)  # the re-scored employee's second opinion is ready before anyone opens their page
    return entry


@router.get("/{employee_id}/history")
def history(employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(HR, AUDITOR))):
    """Every change to this employee's work record, newest first."""
    from app.promotion.labels import format_value, label

    if db.get(Employee, employee_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such employee.")
    rows = db.scalars(select(RecordChange).where(RecordChange.employee_id == employee_id)
                      .order_by(RecordChange.changed_at.desc(), RecordChange.id.desc()))
    return [{"id": r.id, "changed_at": r.changed_at.isoformat(timespec="seconds"), "changed_by": r.changed_by_name,
             "source": r.source, "reason": r.reason, "score_before": r.score_before, "score_after": r.score_after,
             "model_version": r.model_version,
             "changes": [{**c, "label": label(c["field"]),
                          "old_display": format_value(c["field"], c["old"]) if c["old"] is not None else "–",
                          "new_display": format_value(c["field"], c["new"])} for c in json.loads(r.changes_json)]}
            for r in rows]


@router.post("/import")
def import_csv(body: ImportIn, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(hr_only)):
    """
    Check a CSV file of employees, row by row; with save=True, add them all.
    All or nothing: if any row has an error, no one is added, so a file is never half-imported.
    """
    try:
        rows = read_csv(body.csv)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))

    stats, known_departments = model().stats, departments()
    manager_ids = {m.username: m.id for m in managers(db)}
    seen, results, ready = set(), [], []
    for line, row in enumerate(rows, start=2):  # line 1 is the header
        name, department, manager = row.get("full_name", ""), row.get("department", ""), row.get("manager_username", "")
        record, errors, warnings = to_record(row, stats)
        problems = list(errors.values())
        if len(name) < 2:
            problems.insert(0, "Full name is missing.")
        if department not in known_departments:
            problems.insert(0, f"Department '{department}' isn't one of: {', '.join(known_departments)}.")
        if manager and manager not in manager_ids:
            problems.append(f"No manager with username '{manager}'.")
        if (name, department) in seen:
            problems.append("This person appears twice in the file.")
        elif name and same_person_exists(db, name, department):
            problems.append("This person is already in the directory. Edit their record instead.")
        seen.add((name, department))
        results.append({"line": line, "full_name": name, "department": department,
                        "errors": problems, "warnings": list(warnings.values())})
        if not problems:
            ready.append(Employee(full_name=name, department=department, manager_user_id=manager_ids.get(manager),
                                  record_json=json.dumps(record)))

    failed = sum(1 for r in results if r["errors"])
    saved = 0
    if body.save and not failed:
        db.add_all(ready)
        log(db, user, "employees_imported", f"{len(ready)} employees")
        db.commit()
        saved = len(ready)
        joined = {}
        for employee in ready:  # one email per manager, listing everyone added to their team
            if employee.manager_user_id:
                joined.setdefault(employee.manager_user_id, []).append(employee.full_name)
        notify_new_team_members(background, db, joined)
    return {"rows": results, "total": len(results), "failed": failed, "saved": saved}
