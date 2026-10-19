"""
Sign-in codes by email (core/email_codes.py): for the roles in EMAIL_CODE_ROLES, the right password is followed by a
six-digit code emailed to the account. It works once, for ten minutes, only while it is the newest code, and for at
most five tries; a new one can be sent once a minute. Other roles sign in as before.
"""
import os
import re
import shutil
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.accounts.models import User
from app.core import config, email_codes, mailer, totp
from app.core.activity import ActivityEntry
from app.core.database import SessionLocal
from tests.conftest import emails_to, login

HR_EMAIL = "hr@example.org"


@pytest.fixture(autouse=True)
def protect_hr_and_finance(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_CODE_ROLES", {"hr", "finance"})
    shutil.rmtree(os.environ["OUTBOX_DIR"], ignore_errors=True)  # count only this test's emails


def sign_in(client, code=None, username="hr", password="demo1234"):
    body = {"username": username, "password": password, **({"code": code} if code is not None else {})}
    return client.post("/api/auth/login", json=body)


def last_code(address=HR_EMAIL):
    mail = emails_to(address)[-1]
    assert mail["subject"].endswith("sign-in code")
    return "".join(re.search(r"Sign-in code: (\d{3}) (\d{3})", mail["text"]).groups())


def change_user(username, **values):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        for name, value in values.items():
            setattr(user, name, value(getattr(user, name)) if callable(value) else value)
        db.commit()


def test_the_right_password_is_followed_by_a_code_sent_by_email(client):
    asked = sign_in(client)
    assert asked.status_code == 401
    detail = asked.json()["detail"]
    assert detail["code_required"] and detail["method"] == "email" and detail["sent_to"] == "h•@example.org"
    assert detail["retry_in"] == email_codes.RESEND_SECONDS and "h•@example.org" in detail["message"]
    assert len(emails_to(HR_EMAIL)) == 1

    res = sign_in(client, last_code())
    assert res.status_code == 200 and res.json()["user"]["username"] == "hr"
    with SessionLocal() as db:
        assert db.scalar(select(ActivityEntry).where(ActivityEntry.action == "sign_in_code_sent")) is not None


def test_a_code_with_a_space_in_it_works_too(client):
    sign_in(client)
    code = last_code()
    assert sign_in(client, f"{code[:3]} {code[3:]}").status_code == 200


def test_other_roles_sign_in_with_just_their_password(client):
    assert sign_in(client, username="manager").status_code == 200
    assert emails_to("manager@example.org") == []


def test_a_wrong_code_is_refused_and_the_right_one_still_works(client):
    sign_in(client)
    wrong = sign_in(client, "000000" if last_code() != "000000" else "111111")
    assert wrong.status_code == 401
    assert wrong.json()["detail"]["code_required"] and "isn't right" in wrong.json()["detail"]["message"]
    assert sign_in(client, last_code()).status_code == 200


def test_a_code_works_only_once(client):
    sign_in(client)
    code = last_code()
    assert sign_in(client, code).status_code == 200
    assert sign_in(client, code).status_code == 401


def test_an_expired_code_is_refused(client):
    sign_in(client)
    change_user("hr", email_code_expires=lambda t: t - timedelta(minutes=email_codes.CODE_MINUTES + 1))
    assert sign_in(client, last_code()).status_code == 401


def test_a_new_code_waits_a_minute_and_then_replaces_the_old_one(client):
    sign_in(client)
    first = last_code()
    again = sign_in(client)  # straight away: no second email
    assert again.status_code == 401 and 0 < again.json()["detail"]["retry_in"] <= email_codes.RESEND_SECONDS
    assert len(emails_to(HR_EMAIL)) == 1

    change_user("hr", email_code_sent_at=lambda t: t - timedelta(seconds=email_codes.RESEND_SECONDS))
    sign_in(client)
    assert len(emails_to(HR_EMAIL)) == 2
    second = last_code()
    if first != second:  # (one in a million: the same six digits twice)
        assert sign_in(client, first).status_code == 401
    assert sign_in(client, second).status_code == 200


def test_five_wrong_tries_cancel_the_code(client):
    sign_in(client)
    code = last_code()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(email_codes.MAX_ATTEMPTS):
        sign_in(client, wrong)
    assert sign_in(client, code).status_code == 401  # even the right code, now


def test_wrong_codes_count_towards_locking_the_account(client):
    sign_in(client)
    code = last_code()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        sign_in(client, wrong)
    change_user("hr", email_code_sent_at=lambda t: t - timedelta(minutes=5))
    assert sign_in(client).json()["detail"].startswith("Wrong username or password")  # locked: no new code either


def test_a_wrong_password_never_reaches_the_code_step(client):
    res = sign_in(client, password="wrong")
    assert res.status_code == 401 and res.json()["detail"].startswith("Wrong username or password")
    assert emails_to(HR_EMAIL) == []
    sign_in(client)
    assert sign_in(client, last_code(), password="wrong").status_code == 401


def test_an_account_without_an_email_address_is_told_to_ask_for_one(client):
    change_user("hr", email=None)
    res = sign_in(client)
    assert res.status_code == 403 and "administrator" in res.json()["detail"]


def test_someone_with_an_authenticator_app_enters_its_code_instead(client):
    secret = totp.new_secret()
    change_user("hr", totp_secret=secret, totp_enabled=True)
    asked = sign_in(client)
    assert asked.status_code == 401 and asked.json()["detail"]["method"] == "app"
    assert emails_to(HR_EMAIL) == []
    assert sign_in(client, totp.current_code(secret)).status_code == 200


def test_the_code_is_not_kept_in_the_email_log(client):
    sign_in(client)
    with SessionLocal() as db:
        entry = db.scalar(select(mailer.EmailLog).where(mailer.EmailLog.to_address == HR_EMAIL))
        assert entry.kind == "security" and entry.mail_json is None
    admin = login(client, "admin")
    logged = [e for e in client.get("/api/admin/email/log", headers=admin).json()["items"] if e["to"] == HR_EMAIL]
    assert logged and not logged[0]["can_resend"]


def test_the_code_is_not_in_a_download_of_your_own_data(client):
    sign_in(client)
    res = sign_in(client, last_code())
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    account = client.get("/api/privacy/my-data", headers=headers).json()["account"]
    assert not any(key.startswith("email_code") for key in account)


def test_mail_to_example_addresses_is_saved_never_sent(client, monkeypatch):
    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "connect", lambda: pytest.fail("tried to send to an example address"))
    sign_in(client)
    assert len(emails_to(HR_EMAIL)) == 1
    assert mailer.cannot_receive("someone@example.org") and mailer.cannot_receive("a@b.test")
    assert not mailer.cannot_receive("someone@gmail.com")


def test_addresses_are_shown_mostly_hidden():
    assert email_codes.masked("michael@gmail.com") == "m•••••l@gmail.com"
    assert email_codes.masked("hr@example.org") == "h•@example.org"
