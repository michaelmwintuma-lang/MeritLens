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
from app.promotion.features import MODEL_FEATURES, NUMERIC_FEATURES, load_dataset, split_data
from app.promotion.models import Employee

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
        record = {feature: float(row[feature]) for feature in NUMERIC_FEATURES}
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
