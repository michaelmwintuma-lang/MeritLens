"""
Demo employee directory, created the first time the app starts.

The employees are taken from the TEST part of the dataset, so the model has never seen them in training. The
dataset has no names, so each gets a made-up one. The demo manager is given a team, and the demo employee
login is linked to one member of that team.
"""
import json
import random
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core import audit
from app.promotion.features import MODEL_FEATURES, NUMERIC_FEATURES, load_dataset, split_data
from app.promotion.models import Employee
from app.promotion.records import ENTRY_FIELDS

# Inputs HR enters as whole numbers (counts). The dataset has a few as decimals (e.g. 36.4 tasks), which the
# employee form rightly refuses, so they are rounded when the demo directory is made, and once in older databases.
WHOLE = [name for name, _, _, whole, _ in ENTRY_FIELDS if whole]


def whole_numbers(record: dict) -> dict:
    return {k: (float(round(v)) if k in WHOLE and v != round(v) else v) for k, v in record.items()}

DEMO_SIZE = 120
TEAM_SIZE = 12

FIRST_NAMES = ["Amara", "Ben", "Chloe", "Daniel", "Efe", "Fatima", "George", "Hannah", "Ibrahim", "Julia", "Kwame",
               "Laura", "Mateo", "Nadia", "Oliver", "Priya", "Quentin", "Rosa", "Samuel", "Tara", "Umar", "Vera",
               "William", "Ximena", "Yusuf", "Zara"]
LAST_NAMES = ["Adeyemi", "Brooks", "Castillo", "Dubois", "Eze", "Fischer", "Garcia", "Haddad", "Ivanova", "Johnson",
              "Kowalski", "Lindqvist", "Mensah", "Nakamura", "Okafor", "Patel", "Quinn", "Rossi", "Silva", "Tanaka",
              "Usman", "Varga", "Walsh", "Xu", "Yilmaz", "Zimmermann"]


@lru_cache(maxsize=1)
def demo_rows() -> list[dict]:
    """The demo employees' records from the test split (read once and kept in memory)."""
    _, _, test = split_data(load_dataset())
    sample = test.sample(DEMO_SIZE, random_state=42)
    return sample[["employee_id", "department", *MODEL_FEATURES]].to_dict("records")


def unique_names(count: int) -> list[str]:
    """Made-up, unique full names, the same every time."""
    pairs = [f"{first} {last}" for first in FIRST_NAMES for last in LAST_NAMES]
    random.Random(42).shuffle(pairs)
    return pairs[:count]


def seed_demo_employees(db: Session) -> None:
    """Add the demo employees, the manager's team and the demo employee's link, if the directory is empty."""
    if db.scalar(select(Employee).limit(1)) is not None:
        return
    manager = db.scalar(select(User).where(User.username == "manager"))
    employee_login = db.scalar(select(User).where(User.username == "employee"))

    for i, (row, name) in enumerate(zip(demo_rows(), unique_names(DEMO_SIZE))):
        record = whole_numbers({feature: float(row[feature]) for feature in NUMERIC_FEATURES})
        db.add(Employee(
            id=int(row["employee_id"]),
            full_name=name,
            department=row["department"],
            manager_user_id=manager.id if manager and i < TEAM_SIZE else None,
            record_json=json.dumps(record),
        ))
        # The demo employee login belongs to the first member of the demo manager's team
        if i == 0 and employee_login:
            employee_login.employee_id = int(row["employee_id"])
    db.commit()


def round_whole_numbers(db: Session) -> int:
    """
    Once, in a database made before counts were rounded: round them, so every record can be edited on the form.
    The change is tiny (36.4 tasks becomes 36) and is noted in the audit trail. Returns how many records changed.
    """
    changed = 0
    for employee in db.scalars(select(Employee)):
        record = json.loads(employee.record_json)
        fixed = whole_numbers(record)
        if fixed != record:
            employee.record_json = json.dumps(fixed)
            changed += 1
    if changed:
        audit.append(db, "records_normalised", None, "employee", "all", {"records": changed, "fields": WHOLE})
        db.commit()
    return changed
