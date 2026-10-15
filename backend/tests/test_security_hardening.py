"""
Hardening: security headers on every answer; failed sign-ins slowed down per network address (so nobody can lock
accounts or guess passwords at speed); and two-factor sign-in with an authenticator app, which a role can be made to
require.
"""
from app.core import config, totp
from tests.conftest import login


def test_every_answer_carries_the_security_headers(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff" and res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "same-origin" and res.headers["Cache-Control"] == "no-store"


def test_failed_sign_ins_from_one_address_are_slowed_down(client):
    for i in range(20):  # different accounts, so no one account is locked
        assert client.post("/api/auth/login", json={"username": f"nobody{i}", "password": "wrong"}).status_code == 401
    blocked = client.post("/api/auth/login", json={"username": "hr", "password": "demo1234"})
    assert blocked.status_code == 429 and "wait" in blocked.json()["detail"]


def test_two_factor_sign_in_needs_the_password_and_a_code(client):
    headers = login(client, "finance")
    setup = client.post("/api/auth/2fa/setup", headers=headers).json()
    assert setup["link"].startswith("otpauth://totp/") and setup["secret"] in setup["link"]
    assert client.post("/api/auth/2fa/enable", headers=headers, json={"code": "000000"}).status_code == 400
    me = client.post("/api/auth/2fa/enable", headers=headers, json={"code": totp.current_code(setup["secret"])}).json()
    assert me["totp_enabled"]

    asked = client.post("/api/auth/login", json={"username": "finance", "password": "demo1234"})
    assert asked.status_code == 401 and asked.json()["detail"]["code_required"]
    wrong = client.post("/api/auth/login", json={"username": "finance", "password": "demo1234", "code": "123456"})
    assert wrong.status_code == 401
    right = client.post("/api/auth/login", json={"username": "finance", "password": "demo1234", "code": totp.current_code(setup["secret"])})
    assert right.status_code == 200
    # A code alone isn't enough: the password must be right too
    assert client.post("/api/auth/login", json={"username": "finance", "password": "wrong", "code": totp.current_code(setup["secret"])}).status_code == 401

    token = {"Authorization": f"Bearer {right.json()['access_token']}"}
    client.cookies.clear()
    assert client.post("/api/auth/2fa/disable", headers=token, json={"code": totp.current_code(setup["secret"])}).status_code == 400  # no password
    off = client.post("/api/auth/2fa/disable", headers=token, json={"code": totp.current_code(setup["secret"]), "password": "demo1234"})
    assert off.status_code == 200 and not off.json()["totp_enabled"]


def test_a_role_can_be_made_to_use_two_factor_sign_in(client, monkeypatch):
    monkeypatch.setattr(config, "REQUIRE_2FA_ROLES", {"hr"})
    assert client.get("/api/auth/me", headers=login(client, "hr")).json()["must_set_up_2fa"]
    assert not client.get("/api/auth/me", headers=login(client, "manager")).json()["must_set_up_2fa"]


def test_codes_follow_the_standard():
    """RFC 6238's test secret ("12345678901234567890"), at 59 seconds: the SHA-1 code ends 287082."""
    import base64
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp.current_code(secret, now=59) == "287082"
    assert totp.verify(secret, "287082", now=59) and not totp.verify(secret, "287081", now=59)
