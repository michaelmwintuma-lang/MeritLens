"""
Logging that a server can search, and telling the admins when something breaks.

- Every request is logged with an id (also sent back as the X-Request-ID header), method, path, status and time
  taken; never a query string, body or token, which can hold personal data. LOG_FORMAT=json writes one JSON object
  per line (for a log service); the default is plain text. LOG_LEVEL sets how much (INFO by default).
- An unexpected error is logged in full with its request id, the person gets a short message quoting that id, and
  every admin gets an email and a bell notification: at most one per kind of error per ALERT_EVERY_MINUTES, so a
  broken page can't flood anyone's inbox. A failing timer step (scheduler.py) alerts the same way.
- The latest errors are kept in memory for the admin's home page.
"""
import json
import logging
import os
import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

LOG_FORMAT = os.getenv("LOG_FORMAT", "text")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ALERT_EVERY_MINUTES = int(os.getenv("ALERT_EVERY_MINUTES", "60"))
RECENT = 20

log = logging.getLogger("meritlens")
request_log = logging.getLogger("meritlens.requests")
_recent: deque = deque(maxlen=RECENT)
_last_alert: dict[str, float] = {}
_lock = threading.Lock()


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with any extra fields given to the log call."""
    STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        entry = {"at": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
                 "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        entry.update({k: v for k, v in vars(record).items() if k not in self.STANDARD})
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure() -> None:
    """Set up the app's log output once (called at start-up)."""
    logger = logging.getLogger("meritlens")
    if getattr(logger, "_configured", False):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if LOG_FORMAT == "json" else
                         logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    logger._configured = True


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def recent_errors() -> list[dict]:
    with _lock:
        return list(reversed(_recent))


def clear() -> None:
    """Tests: forget earlier errors and alerts."""
    with _lock:
        _recent.clear()
        _last_alert.clear()


def record_error(where: str, error: BaseException, reference: str) -> bool:
    """Keep the error for the admin's page. Returns True when the admins should be alerted (not alerted lately)."""
    signature = f"{where}:{type(error).__name__}"
    now = time.monotonic()
    with _lock:
        _recent.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reference": reference,
                        "where": where, "error": f"{type(error).__name__}: {str(error)[:200]}"})
        last = _last_alert.get(signature)
        if last is not None and now - last < ALERT_EVERY_MINUTES * 60:
            return False
        _last_alert[signature] = now
        return True


def alert_admins(where: str, error: str, reference: str) -> None:
    """Email (and bell-notify) every active admin with an email address. Never raises."""
    try:
        from sqlalchemy import select

        from app.accounts.models import User
        from app.core import email_templates as templates
        from app.core import mailer
        from app.core.database import SessionLocal
        from app.core.roles import ADMIN
        with SessionLocal() as db:
            admins = [(u.email, u.full_name) for u in db.scalars(
                select(User).where(User.role == ADMIN, User.is_active.is_(True), User.email.is_not(None)))]
        for email, name in admins:
            mailer.send(email, templates.system_error(name, where, error, reference))
    except Exception:  # noqa: BLE001 - an alert that fails must not cause another error
        log.exception("Could not alert the admins about error %s", reference)


def report(where: str, error: BaseException, reference: str | None = None, alert_now: bool = True) -> tuple[str, bool]:
    """
    Log an unexpected error in full and decide whether to alert. Returns (reference, should_alert); with alert_now
    the alert is sent here (the timer); a request sends it after answering (main.py).
    """
    reference = reference or new_request_id()
    log.error("Unexpected error in %s (reference %s)", where, reference, exc_info=error,
              extra={"reference": reference, "where": where})
    should = record_error(where, error, reference)
    if should and alert_now:
        alert_admins(where, f"{type(error).__name__}: {str(error)[:300]}", reference)
    return reference, should
