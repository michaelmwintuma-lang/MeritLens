"""
One-off script: add a second HR account (hr2 / Kwame Mensah) to the database
so the Four-Eyes rule can be turned on.
Run from the project root:
    python scripts/add_hr2.py
"""
import sys
import os

# Point imports at the backend package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["SKIP_ENV_FILE"] = "0"   # let it load backend/.env

from app.core.database import SessionLocal, engine, Base
from app.core import config  # noqa: F401 – loads .env
from app.core.security import hash_password
from app.accounts.models import User

# Keep these consistent with the rest of the demo accounts
USERNAME   = "hr2"
FULL_NAME  = "Kwame Mensah"
EMAIL      = "kwame.hr@meritlens.local"
JOB_TITLE  = "Senior HR Specialist"
PASSWORD   = "demo1234"          # same temp password as all demo accounts
ROLE       = "hr"

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == USERNAME).first()
    if existing:
        print(f"Account '{USERNAME}' already exists (id={existing.id}). Nothing changed.")
        sys.exit(0)

    u = User(
        username=USERNAME,
        full_name=FULL_NAME,
        email=EMAIL,
        role=ROLE,
        job_title=JOB_TITLE,
        is_active=True,
        must_change_password=True,
        password_hash=hash_password(PASSWORD),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    print(f"Created: id={u.id}  username={u.username}  role={u.role}")
    print(f"  Full name : {u.full_name}")
    print(f"  Email     : {u.email}")
    print(f"  Password  : {PASSWORD}  (must change on first sign-in)")
finally:
    db.close()
