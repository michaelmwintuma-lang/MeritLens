"""Fictional demo accounts, one per role, created the first time the app starts on an empty database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import DEMO_PASSWORD
from app.core.roles import ADMIN, EMPLOYEE, FINANCE, HR, MANAGER
from app.core.security import hash_password

DEMO_ACCOUNTS = [
    ("admin", "Ada Admin", ADMIN),
    ("hr", "Hana Reviewer", HR),
    ("manager", "Mo Manager", MANAGER),
    ("employee", "Eli Employee", EMPLOYEE),
    ("finance", "Fay Finance", FINANCE),
]


def seed_demo_accounts(db: Session) -> None:
    """Add the demo accounts if there are no users yet. Existing data is never changed."""
    if db.scalar(select(User).limit(1)) is not None:
        return
    for username, full_name, role in DEMO_ACCOUNTS:
        db.add(User(username=username, full_name=full_name, role=role, password_hash=hash_password(DEMO_PASSWORD),
                    email=f"{username}@example.org"))  # example.org is reserved for examples: nobody receives it
    db.commit()
