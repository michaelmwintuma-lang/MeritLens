"""Passwords, login tokens (JWT) and role checks."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import SECRET_KEY, TOKEN_MINUTES
from app.core.database import get_db

PBKDF2_ITERATIONS = 200_000


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
def create_token(user_id: int) -> str:
    """Signed token that proves who the user is. It expires after TOKEN_MINUTES."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm="HS256")


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
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise NOT_SIGNED_IN
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise NOT_SIGNED_IN
    return user


def require_roles(*roles: str):
    """Route dependency: only users with one of these roles get through; everyone else gets 403."""
    def check(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not have access to this.")
        return user
    return check
