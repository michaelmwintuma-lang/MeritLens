"""Passwords, login tokens (JWT) and role checks."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import SECRET_KEY, TOKEN_MINUTES
from app.core.database import get_db

# Rounds of hashing for new passwords. Each stored hash records its own count, so changing this
# never breaks existing passwords. Only the tests lower it (tests/conftest.py), to save minutes of hashing.
PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "200000"))
MAX_FAILED_LOGINS = 5     # wrong passwords in a row before the account is locked
LOCK_MINUTES = 15


# ─── Passwords ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password with a random salt (PBKDF2-SHA256). The password itself is never stored."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time."""
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def temporary_password() -> str:
    """A random password an admin gives to a new user, who should change it at first sign-in."""
    return secrets.token_urlsafe(9)


# ─── Login tokens ─────────────────────────────────────────────────────────────
def create_token(user) -> str:
    """
    Signed token that proves who the user is. It expires after TOKEN_MINUTES, or earlier when the user's
    token_version goes up (password changed or reset, or signed out).
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "ver": user.token_version or 0, "exp": expires}, SECRET_KEY, algorithm="HS256")


def withdraw_tokens(user) -> None:
    """Make every login token this user already has stop working. The caller commits."""
    user.token_version = (user.token_version or 0) + 1


bearer = HTTPBearer(auto_error=False)
NOT_SIGNED_IN = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    """
    The signed-in user, read fresh from the database on every request. The token only says *who* the user is;
    their role and active status come from the database, so a deactivation or role change applies at once.
    """
    if credentials is None:
        raise NOT_SIGNED_IN
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id, version = int(payload["sub"]), int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise NOT_SIGNED_IN
    user = db.get(User, user_id)
    if user is None or not user.is_active or version != (user.token_version or 0):
        raise NOT_SIGNED_IN
    return user


def require_roles(*roles: str):
    """Route dependency: only users with one of these roles get through; everyone else gets 403."""
    def check(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not have access to this.")
        return user
    return check
