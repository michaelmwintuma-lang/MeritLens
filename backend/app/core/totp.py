"""
Two-factor sign-in codes: the six-digit codes an authenticator app (Google Authenticator, Microsoft Authenticator,
1Password...) shows, changing every 30 seconds. This is the standard method (TOTP, RFC 6238, with SHA-1 as the apps
expect), written out here so it needs no extra library.

The secret is shared once, when the person sets it up (as a QR code or typed in). A code is accepted for the
current 30 seconds and the one before or after it, to allow for clocks that are slightly out.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from app.core.config import APP_NAME

STEP, DIGITS = 30, 6


def new_secret() -> str:
    """A random secret, in the base32 form authenticator apps take."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code_at(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10 ** DIGITS).zfill(DIGITS)


def current_code(secret: str, now: float | None = None) -> str:
    return code_at(secret, int((now or time.time()) // STEP))


def verify(secret: str, code: str | None, now: float | None = None) -> bool:
    """Whether the code is right for now (or 30 seconds either side)."""
    code = (code or "").replace(" ", "")
    if not code.isdigit() or len(code) != DIGITS:
        return False
    counter = int((now or time.time()) // STEP)
    return any(hmac.compare_digest(code_at(secret, counter + d), code) for d in (-1, 0, 1))


def setup_link(secret: str, username: str) -> str:
    """The otpauth:// link an authenticator app reads (from a QR code)."""
    return (f"otpauth://totp/{quote(APP_NAME)}:{quote(username)}?secret={secret}&issuer={quote(APP_NAME)}"
            f"&digits={DIGITS}&period={STEP}")
