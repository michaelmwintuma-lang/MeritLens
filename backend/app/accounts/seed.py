"""Fictional demo accounts, one per role, created the first time the app starts on an empty database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import DEMO_PASSWORD
from app.core.roles import ADMIN, AUDITOR, EMPLOYEE, FINANCE, HR, MANAGER
from app.core.security import hash_password

DEMO_ACCOUNTS = [
    ("admin", "Ada Admin", ADMIN),
    ("hr", "Hana Reviewer", HR),
    ("manager", "Mo Manager", MANAGER),
    ("employee", "Eli Employee", EMPLOYEE),
    ("finance", "Fay Finance", FINANCE),
    ("auditor", "Aria Auditor", AUDITOR),
]


def demo_user(username: str, full_name: str, role: str) -> User:
    # example.org is reserved for examples: nobody receives it
    return User(username=username, full_name=full_name, role=role, password_hash=hash_password(DEMO_PASSWORD),
                email=f"{username}@example.org")


def seed_demo_accounts(db: Session) -> None:
    """
    Add the demo accounts if there are no users yet. Existing data is never changed.
    A demo database made before a role existed gets that role's demo account too, so every role can be tried. Only
    a demo database qualifies (its "admin" account still has its demo address), never a real one.
    """
    if db.scalar(select(User).limit(1)) is None:
        db.add_all(demo_user(*account) for account in DEMO_ACCOUNTS)
        db.commit()
        return
    if db.scalar(select(User).where(User.username == "admin", User.email == "admin@example.org")) is None:
        return
    for username, full_name, role in DEMO_ACCOUNTS:
        if db.scalar(select(User).where(User.username == username)) is None:
            db.add(demo_user(username, full_name, role))
    db.commit()
