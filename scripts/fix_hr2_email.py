"""
Fix hr2's email to a real deliverable address so the email OTP code can be sent.
Run from project root: python scripts/fix_hr2_email.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["SKIP_ENV_FILE"] = "0"

from app.core.database import SessionLocal
from app.accounts.models import User

# Change this to any real email you can check right now
NEW_EMAIL = "mwintumamichael@gmail.com"   # same as admin – fine for demo

db = SessionLocal()
try:
    u = db.query(User).filter(User.username == "hr2").first()
    if not u:
        print("hr2 not found!")
    else:
        old = u.email
        u.email = NEW_EMAIL
        db.commit()
        print(f"hr2 email updated: {old!r}  ->  {NEW_EMAIL!r}")
finally:
    db.close()
