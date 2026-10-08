"""Step 1 tests: signing in, passwords, and role checks on the backend."""
import pytest

from app.core.security import hash_password, verify_password
from tests.conftest import login

ROLES = ["admin", "hr", "manager", "employee"]


# ─── Passwords ────────────────────────────────────────────────────────────────
def test_passwords_are_hashed_with_a_salt():
    first, second = hash_password("secret123"), hash_password("secret123")
    assert "secret123" not in first
    assert first != second  # a different random salt each time
    assert verify_password("secret123", first)
    assert not verify_password("wrong", first)


# ─── Signing in ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("username", ROLES)
def test_each_demo_account_can_sign_in(client, username):
    me = client.get("/api/auth/me", headers=login(client, username)).json()
    assert me["username"] == username and me["role"] == username
    assert "password_hash" not in me


def test_wrong_password_and_unknown_user_get_the_same_message(client):
    wrong = client.post("/api/auth/login", json={"username": "hr", "password": "nope"})
    unknown = client.post("/api/auth/login", json={"username": "nobody", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_requests_without_a_valid_token_are_refused(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_changing_password(client):
    headers = login(client, "employee")
    assert client.post("/api/auth/change-password", headers=headers,
                       json={"current_password": "wrong", "new_password": "newpass123"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=headers,
                       json={"current_password": "demo1234", "new_password": "newpass123"}).status_code == 200
    login(client, "employee", "newpass123")


# ─── Roles: only the admin manages accounts ───────────────────────────────────
@pytest.mark.parametrize("username", ["hr", "manager", "employee"])
def test_non_admins_cannot_manage_accounts(client, username):
    headers = login(client, username)
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    new = {"username": "someone", "full_name": "Some One", "email": "some.one@example.org", "role": "employee"}
    assert client.post("/api/admin/users", headers=headers, json=new).status_code == 403


@pytest.mark.parametrize("role", ROLES)
def test_admin_creates_an_account_for_every_role(client, role):
    admin = login(client, "admin")
    res = client.post("/api/admin/users", headers=admin, json={"username": f"new.{role}", "full_name": "New Person", "email": f"new.{role}@example.org", "role": role})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["user"]["role"] == role and body["user"]["must_change_password"] is True
    # The new person signs in with the temporary password
    me = client.get("/api/auth/me", headers=login(client, f"new.{role}", body["temporary_password"])).json()
    assert me["role"] == role


def test_account_rules(client):
    admin = login(client, "admin")
    assert client.post("/api/admin/users", headers=admin, json={"username": "hr", "full_name": "Dup", "email": "dup@example.org", "role": "hr"}).status_code == 409
    assert client.post("/api/admin/users", headers=admin, json={"username": "x.y", "full_name": "Bad", "email": "xy@example.org", "role": "superuser"}).status_code == 422
    # Link to a real employee who has no login yet (the demo employee login already uses one)
    taken = client.get("/api/auth/me", headers=login(client, "employee")).json()["employee_id"]
    free = next(e["id"] for e in client.get("/api/promotion/employees", headers=login(client, "hr")).json()["employees"]
                if e["id"] != taken)
    first = {"username": "linked.one", "full_name": "One", "email": "one@example.org", "role": "employee", "employee_id": free}
    second = {"username": "linked.two", "full_name": "Two", "email": "two@example.org", "role": "employee", "employee_id": free}
    assert client.post("/api/admin/users", headers=admin, json=first).status_code == 201
    assert client.post("/api/admin/users", headers=admin, json=second).status_code == 409  # one login per employee
    missing = {"username": "linked.three", "full_name": "Three", "email": "three@example.org", "role": "employee", "employee_id": 999999999}
    assert client.post("/api/admin/users", headers=admin, json=missing).status_code == 404  # must exist


def test_deactivated_accounts_are_locked_out_at_once(client):
    admin = login(client, "admin")
    employee = login(client, "employee")
    user_id = client.get("/api/auth/me", headers=employee).json()["id"]
    assert client.patch(f"/api/admin/users/{user_id}/active", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/auth/me", headers=employee).status_code == 401  # their existing token stops working
    assert client.post("/api/auth/login", json={"username": "employee", "password": "demo1234"}).status_code == 401


def test_admin_cannot_lock_themselves_out(client):
    admin = login(client, "admin")
    admin_id = client.get("/api/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/api/admin/users/{admin_id}/active", headers=admin, json={"is_active": False}).status_code == 400


def test_admin_resets_a_forgotten_password(client):
    admin = login(client, "admin")
    user_id = client.get("/api/auth/me", headers=login(client, "manager")).json()["id"]
    temp = client.post(f"/api/admin/users/{user_id}/reset-password", headers=admin).json()["temporary_password"]
    assert client.get("/api/auth/me", headers=login(client, "manager", temp)).json()["must_change_password"] is True


# ─── Sign-in lockout and withdrawn tokens (review S3, S4) ─────────────────────
def test_five_wrong_passwords_lock_the_account_for_15_minutes(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "hr", "password": "nope"}).status_code == 401
    # Locked: even the right password is refused, with the same message as any failed sign-in
    locked = client.post("/api/auth/login", json={"username": "hr", "password": "demo1234"})
    unknown = client.post("/api/auth/login", json={"username": "nobody", "password": "nope"})
    assert locked.status_code == 401 and locked.json() == unknown.json()
    # After 15 minutes it opens again
    from datetime import datetime, timedelta
    from app.accounts.models import User
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="hr").one()
        assert user.locked_until - datetime.utcnow() > timedelta(minutes=14)
        user.locked_until = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    login(client, "hr")


def test_a_right_password_resets_the_count_of_wrong_ones(client):
    for _ in range(4):
        client.post("/api/auth/login", json={"username": "hr", "password": "nope"})
    login(client, "hr")
    for _ in range(4):
        client.post("/api/auth/login", json={"username": "hr", "password": "nope"})
    login(client, "hr")  # still not locked: the count started again


def test_an_admin_password_reset_unlocks_the_account(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "employee", "password": "nope"})
    admin = login(client, "admin")
    user_id = next(u["id"] for u in client.get("/api/admin/users", headers=admin).json() if u["username"] == "employee")
    temporary = client.post(f"/api/admin/users/{user_id}/reset-password", headers=admin).json()["temporary_password"]
    login(client, "employee", temporary)


def test_signing_out_withdraws_the_token(client):
    headers = login(client, "manager")
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_changing_the_password_signs_out_other_devices_but_not_this_one(client):
    other_device = login(client, "employee")
    res = client.post("/api/auth/change-password", headers=other_device,
                      json={"current_password": "demo1234", "new_password": "newpass123"})
    assert client.get("/api/auth/me", headers=other_device).status_code == 401
    fresh = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=fresh).json()["username"] == "employee"


def test_an_admin_password_reset_signs_the_person_out(client):
    headers = login(client, "manager")
    admin = login(client, "admin")
    user_id = next(u["id"] for u in client.get("/api/admin/users", headers=admin).json() if u["username"] == "manager")
    client.post(f"/api/admin/users/{user_id}/reset-password", headers=admin)
    assert client.get("/api/auth/me", headers=headers).status_code == 401
