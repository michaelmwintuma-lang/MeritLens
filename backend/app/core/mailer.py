"""
Sending emails.

Each email is described once (subject, heading, short paragraphs, a few details, an optional button) and sent in two
versions: a branded HTML one and a plain-text one for simple mail programs.

With a mail server configured in backend/.env (for example Gmail with an app password), emails are sent. Without
one, each email is saved in backend/instance/outbox/ instead, so nothing is lost and the admin is told which
happened.

Every email is recorded in the delivery log (EmailLog): who it went to, its subject, whether it was sent, and any
error. One the mail server didn't accept is tried again later, waiting longer each time (RETRY_MINUTES), and the
admin can resend it from the Email page. An email's content is kept only until it is delivered (it may hold a
temporary password); after that only who, what subject and when remain.

An email with a "notice" (email_templates.py) also adds a line to the recipient's notification bell, if they have
an account, so the bell and the email come from the same event.
"""
import html
import json
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr

from sqlalchemy import DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.accounts.models import User
from app.core import notifications
from app.core.config import APP_NAME, APP_URL, OUTBOX_DIR, SMTP
from app.core.database import Base, SessionLocal

# After a failed attempt, wait this many minutes before the next; after the last, give up (the admin can resend)
RETRY_MINUTES = [1, 5, 15, 60, 240]


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    to_address: Mapped[str] = mapped_column(String(200), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="routine")    # security or routine
    # queued, sent, saved (no mail server: in the outbox folder), failed (will be tried again), gave_up,
    # held (for the recipient's daily digest), in_digest (went out in a digest)
    status: Mapped[str] = mapped_column(String(10), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    mail_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # the content, until it is delivered


def is_configured() -> bool:
    return bool(SMTP["host"] and SMTP["user"] and SMTP["password"])


def _text(mail: dict) -> str:
    lines = [mail["greeting"], ""]
    for paragraph in mail["paragraphs"]:
        lines += [paragraph, ""]
    for label, value in mail.get("details", []):
        lines.append(f"  {label}: {value}")
    if mail.get("details"):
        lines.append("")
    if mail.get("button"):
        lines += [f"{mail['button'][0]}: {mail['button'][1]}", ""]
    if mail.get("note"):
        lines += [mail["note"], ""]
    lines.append(APP_NAME)
    return "\n".join(lines)


def _html(mail: dict) -> str:
    e = html.escape
    paragraphs = "".join(f'<p style="margin:0 0 14px">{e(p)}</p>' for p in mail["paragraphs"])
    details = ""
    if mail.get("details"):
        rows = "".join(
            f'<tr><td style="padding:6px 16px 6px 0;color:#64748b;white-space:nowrap">{e(label)}</td>'
            f'<td style="padding:6px 0;font-weight:600;font-family:{"Consolas,monospace" if label in ("Username", "Temporary password", "Case") else "inherit"}">{e(value)}</td></tr>'
            for label, value in mail["details"])
        details = f'<table style="margin:4px 0 18px;border-collapse:collapse;background:#f8fafc;border:1px solid #e6e9ef;border-radius:10px"><tbody><tr><td style="padding:10px 16px"><table>{rows}</table></td></tr></tbody></table>'
    button = ""
    if mail.get("button"):
        label, url = mail["button"]
        button = (f'<p style="margin:6px 0 20px"><a href="{e(url)}" style="display:inline-block;background:#0F2A44;color:#ffffff;'
                  f'text-decoration:none;font-weight:600;padding:11px 20px;border-radius:10px">{e(label)}</a></p>')
    note = f'<p style="margin:0;color:#64748b;font-size:13px">{e(mail["note"])}</p>' if mail.get("note") else ""
    return f"""<!doctype html><html><body style="margin:0;background:#f5f7fa;font-family:Segoe UI,Arial,sans-serif;color:#0f172a">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fa;padding:28px 12px"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #e6e9ef;border-radius:16px">
<tr><td style="padding:20px 28px;border-bottom:1px solid #e6e9ef;font-weight:800;font-size:15px">{html.escape(APP_NAME)}
<span style="display:block;font-size:11px;letter-spacing:.08em;color:#64748b;font-weight:700">STAFF PLATFORM</span></td></tr>
<tr><td style="padding:26px 28px 24px;font-size:15px;line-height:1.55">
<h1 style="font-size:21px;margin:0 0 16px">{e(mail["heading"])}</h1>
<p style="margin:0 0 14px">{e(mail["greeting"])}</p>{paragraphs}{details}{button}{note}
</td></tr></table>
<p style="color:#94a3b8;font-size:12px;margin:14px 0 0">Sent automatically by {html.escape(APP_NAME)}.</p>
</td></tr></table></body></html>"""


def build(to: str, mail: dict) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = mail["subject"]
    message["From"] = formataddr((SMTP["sender_name"], SMTP["sender"]))
    message["To"] = to
    if mail.get("reply_to"):  # e.g. a demo request: "Reply" goes straight to the person who asked
        message["Reply-To"] = mail["reply_to"]
    message.set_content(_text(mail))
    message.add_alternative(_html(mail), subtype="html")
    return message


def send(to: str, mail: dict) -> dict:
    """
    Send one email (or save it in the outbox), record it in the delivery log, and add the recipient's bell
    notification. Returns what happened, in words the admin can read. Called in the background after a request.
    """
    with SessionLocal() as db:
        entry = EmailLog(to_address=to, subject=mail["subject"][:200], kind=mail.get("kind", "routine"),
                         status="queued", attempts=0, mail_json=json.dumps(mail))
        db.add(entry)
        recipient = notify(db, to, mail)
        if entry.kind == "routine" and recipient is not None and recipient.email_mode == "daily":
            entry.status = "held"  # it goes out in tomorrow morning's digest (digests.py); the bell has it already
            db.commit()
            return {"sent": False, "detail": f"Held for {to}'s daily digest."}
        result = deliver(entry)
        db.commit()
        return result


def notify(db: Session, to: str, mail: dict) -> User | None:
    """
    The bell line for an email with a "notice", for the account with that address (if there is one). Returns that
    account, so the caller knows how its owner wants emails.
    """
    user = db.scalar(select(User).where(func.lower(User.email) == to.lower(), User.is_active.is_(True)))
    if user is not None and mail.get("notice"):
        button = mail.get("button")
        notifications.add(db, user.id, mail["notice"], button[1].removeprefix(APP_URL) if button else None)
    return user


def connect() -> smtplib.SMTP:
    """A secured connection to the mail server: SSL from the start (port 465), or upgraded with STARTTLS (587)."""
    if SMTP["security"] == "ssl":
        return smtplib.SMTP_SSL(SMTP["host"], SMTP["port"], timeout=20)
    server = smtplib.SMTP(SMTP["host"], SMTP["port"], timeout=20)
    server.starttls()
    return server


def deliver(entry: EmailLog) -> dict:
    """One attempt at delivering a logged email. Updates the entry; the caller commits."""
    message = build(entry.to_address, json.loads(entry.mail_json))
    entry.attempts += 1
    if not is_configured():
        entry.status, entry.next_attempt_at = "saved", None
        return {"sent": False, "detail": f"No mail server is set up, so the email was saved to {_save(message)}."}
    try:
        with connect() as server:
            server.login(SMTP["user"], SMTP["password"])
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        reason = ("the mail server refused the username or app password" if isinstance(error, smtplib.SMTPAuthenticationError)
                  else f"the mail server couldn't be reached ({error.__class__.__name__})")
        entry.last_error = reason
        if entry.attempts <= len(RETRY_MINUTES):
            entry.status = "failed"
            entry.next_attempt_at = now() + timedelta(minutes=RETRY_MINUTES[entry.attempts - 1])
        else:
            entry.status, entry.next_attempt_at = "gave_up", None
        saved = f" Saved to {_save(message)} too." if entry.attempts == 1 else ""
        later = " It will be tried again automatically." if entry.status == "failed" else " No more attempts: resend it from the Email page."
        return {"sent": False, "detail": f"Not sent: {reason}.{later}{saved}"}
    entry.status, entry.sent_at, entry.next_attempt_at, entry.last_error = "sent", now(), None, None
    entry.mail_json = None  # delivered: the content (which may hold a temporary password) is no longer kept
    return {"sent": True, "detail": f"Emailed to {entry.to_address}."}


def retry_due() -> int:
    """Try again every failed email whose next attempt is due. Returns how many were tried (the scheduler calls it)."""
    with SessionLocal() as db:
        due = list(db.scalars(select(EmailLog).where(EmailLog.status == "failed", EmailLog.next_attempt_at <= now())))
        for entry in due:
            deliver(entry)
        db.commit()
        return len(due)


def resend(db: Session, entry: EmailLog) -> dict:
    """The admin resends a logged email (one not delivered: its content is still kept). The caller commits."""
    if entry.mail_json is None:
        raise ValueError("This email was delivered, so its content is no longer kept.")
    entry.attempts = 0 if entry.status == "gave_up" else entry.attempts
    return deliver(entry)


def _save(message: EmailMessage) -> str:
    """Write the email to the outbox folder; return its path relative to the backend folder."""
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    who = str(message["To"]).split("@")[0].replace("/", "_")
    path = OUTBOX_DIR / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{who}.eml"
    path.write_bytes(bytes(message))
    return f"instance/outbox/{path.name}"


def link(path: str) -> str:
    """A full link into the website, for buttons in emails."""
    return f"{APP_URL}{path}"
