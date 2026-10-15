"""
Work done on a timer while the app runs, in one background thread:

- every minute: try again any email the mail server didn't accept (mailer.retry_due)
- every hour: send the reminders that are due (reminders.run_due), each only once
- every morning at DIGEST_HOUR: send the daily digest to people who chose it (digests.send_due), and remove
  personal data past its retention period (privacy/retention.py)

Started with the app (main.py) unless SCHEDULER=0 (the tests run each step directly instead). A problem in one step
is written to the log and never stops the others or the app.
"""
import logging
import threading
from datetime import datetime

from app.core.config import DIGEST_HOUR, SCHEDULER_ON
from app.core.database import SessionLocal

log = logging.getLogger("meritlens.scheduler")
_stop = threading.Event()
_thread: threading.Thread | None = None


def _safely(name, step):
    try:
        step()
    except Exception:  # noqa: BLE001 - keep the scheduler alive, and say what went wrong
        log.exception("Scheduled step failed: %s", name)


def _reminders():
    from app.core import reminders
    with SessionLocal() as db:
        reminders.run_due(db)


def _digests():
    from app.core import digests
    with SessionLocal() as db:
        digests.send_due(db)


def _retention():
    from app.privacy import retention
    with SessionLocal() as db:
        retention.run(db)


def _loop():
    from app.core import mailer
    last_hour, last_digest_day = None, None
    while not _stop.is_set():
        _safely("email retries", mailer.retry_due)
        current = datetime.now()
        if current.strftime("%Y%m%d%H") != last_hour:
            last_hour = current.strftime("%Y%m%d%H")
            _safely("reminders", _reminders)
        if current.hour >= DIGEST_HOUR and current.date() != last_digest_day:
            last_digest_day = current.date()
            _safely("daily digests", _digests)
            _safely("retention", _retention)
        _stop.wait(60)


def start() -> None:
    global _thread
    if not SCHEDULER_ON or (_thread is not None and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="meritlens-scheduler", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
