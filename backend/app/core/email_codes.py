"""
Sign-in codes by email: a second step at sign-in for the roles in EMAIL_CODE_ROLES (e.g. admin, HR, finance,
auditor), whose accounts can see everyone's records, decide promotions, approve pay or manage accounts.

After the right password, a random six-digit code is emailed to the account's address. Signing in then needs the
password and that code. A code:
- works for CODE_MINUTES, and only once;
- is replaced by the next one sent, so only the newest code works;
- is cancelled after MAX_ATTEMPTS wrong tries (wrong tries also count towards locking the account, like wrong
  passwords);
- can be sent again only after RESEND_SECONDS, so nobody can flood a mailbox;
- is stored only as a keyed hash, so the database never holds a code that could be used.

Someone who has an authenticator app set up (core/totp.py) enters the app's code instead: it is stronger, since
it doesn't depend on the email account.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.accounts.models import User
from app.core import config

CODE_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def required(user: User) -> bool:
    """This person signs in with a code from their email (their role needs one, and they don't use an app)."""
    return user.role in config.EMAIL_CODE_ROLES and not user.totp_enabled


def masked(address: str) -> str:
    """The address with most of its name hidden, to show where the code went: "michael@gmail.com" -> "m•••••l@gmail.com"."""
    name, _, domain = address.partition("@")
    hidden = name[0] + "•" * max(len(name) - 2, 1) + (name[-1] if len(name) > 2 else "")
    return f"{hidden}@{domain}"


def _hash(user: User, code: str) -> str:
    # Keyed with the app's secret and the account, so a copied database can't be used to look codes up
    return hmac.new(config.SECRET_KEY.encode(), f"{user.id}:{code}".encode(), hashlib.sha256).hexdigest()


def wait_seconds(user: User) -> int:
    """How long until another code may be sent (0: now)."""
    if user.email_code_sent_at is None:
        return 0
    return max(0, RESEND_SECONDS - int((now() - user.email_code_sent_at).total_seconds()))


def has_live_code(user: User) -> bool:
    return bool(user.email_code_hash and user.email_code_expires and user.email_code_expires > now())


def issue(user: User) -> str:
    """A new code for this person, replacing any earlier one. Returns the code to email; the caller commits."""
    code = f"{secrets.randbelow(10 ** 6):06d}"
    user.email_code_hash, user.email_code_attempts = _hash(user, code), 0
    user.email_code_sent_at, user.email_code_expires = now(), now() + timedelta(minutes=CODE_MINUTES)
    return code


def clear(user: User) -> None:
    user.email_code_hash = user.email_code_expires = None
    user.email_code_attempts = 0


def check(user: User, code: str | None) -> bool:
    """
    Whether the code is this person's current one. A right code is used up; a wrong one counts as a try, and the
    code is cancelled after MAX_ATTEMPTS. The caller commits.
    """
    if not has_live_code(user):
        return False
    given = "".join((code or "").split())  # "123 456" and "123456" are the same code
    if given.isdigit() and hmac.compare_digest(_hash(user, given), user.email_code_hash):
        clear(user)
        return True
    user.email_code_attempts = (user.email_code_attempts or 0) + 1
    if user.email_code_attempts >= MAX_ATTEMPTS:
        clear(user)
    return False
