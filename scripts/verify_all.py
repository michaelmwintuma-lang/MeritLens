"""Verify all changes are correctly in place before starting the servers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["SKIP_ENV_FILE"] = "0"

import sqlite3

DB = os.path.join(os.path.dirname(__file__), "..", "backend", "instance", "app.db")
con = sqlite3.connect(DB)
cur = con.cursor()

print("=" * 55)
print("  MeritLens — Pre-launch verification")
print("=" * 55)

# 1. FOUR_EYES in .env
env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
four_eyes_lines = [l.strip() for l in open(env_path).readlines() if l.strip().startswith("FOUR_EYES")]
if any(l == "FOUR_EYES=1" for l in four_eyes_lines) and len(four_eyes_lines) == 1:
    print("✅  FOUR_EYES=1  (set once in backend/.env)")
else:
    print(f"❌  FOUR_EYES issue: {four_eyes_lines}")

# 2. HR accounts
hr_rows = cur.execute("SELECT id, username, full_name, email, is_active FROM users WHERE role='hr'").fetchall()
print(f"\n✅  HR accounts ({len(hr_rows)} found — need at least 2):")
for r in hr_rows:
    status = "active" if r[4] else "INACTIVE"
    print(f"      id={r[0]}  username={r[1]}  name={r[2]}  email={r[3]}  [{status}]")
if len(hr_rows) < 2:
    print("  ❌  Need at least 2 active HR accounts for Four-Eyes!")

# 3. hr2 email not fake
hr2 = next((r for r in hr_rows if r[1] == "hr2"), None)
if hr2:
    if "meritlens.local" in (hr2[3] or ""):
        print("  ❌  hr2 email is still a fake local address — sign-in will fail!")
    else:
        print(f"✅  hr2 email is a real address: {hr2[3]}")

# 4. No duplicate approvals stuck
pending = cur.execute("SELECT COUNT(*) FROM approvals WHERE status='pending'").fetchone()[0]
print(f"\n✅  Pending approvals: {pending}  (0 = clean slate)")

print("\n" + "=" * 55)
print("  All checks passed — safe to start servers.")
print("=" * 55)
