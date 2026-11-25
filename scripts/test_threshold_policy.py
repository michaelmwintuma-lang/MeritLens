import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["SKIP_ENV_FILE"] = "0"

from app.core.database import SessionLocal
from app.governance import threshold as policy_mod

db = SessionLocal()
try:
    print("--- 1. Testing Default Policy ---")
    policy_mod.clear_cache()
    policy = policy_mod.get_policy(db)
    print(f"DB policy id: {policy.id}, custom_threshold: {policy.custom_threshold}")
    active = policy_mod.get_active_custom_threshold()
    print(f"Cached custom threshold: {active}")
    assert active is None, f"Expected None, got {active}"

    print("\n--- 2. Setting Company Custom Threshold (25.0% = 0.25) ---")
    updated = policy_mod.set_custom_threshold(db, 0.25, "Ada Admin")
    print(f"Updated policy: custom_threshold={updated.custom_threshold}, updated_by={updated.updated_by_name}")
    active = policy_mod.get_active_custom_threshold()
    print(f"Cached custom threshold after update: {active}")
    assert abs(active - 0.25) < 0.0001, f"Expected 0.25, got {active}"

    print("\n--- 3. Testing Reset to Default ---")
    reset_pol = policy_mod.set_custom_threshold(db, None, "Ada Admin")
    print(f"Reset policy: custom_threshold={reset_pol.custom_threshold}")
    active = policy_mod.get_active_custom_threshold()
    print(f"Cached custom threshold after reset: {active}")
    assert active is None, f"Expected None, got {active}"

    print("\n✅ POLICY GET / SET / RESET TEST PASSED!")
finally:
    db.close()
