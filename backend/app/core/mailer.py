"""
Sending emails.

Each email is described once (subject, heading, short paragraphs, a few details, an optional button) and sent in two
versions: a branded HTML one and a plain-text one for simple mail programs.

With a mail server configured in backend/.env (for example Gmail with an app password), emails are sent. Without
one, each email is saved in backend/instance/outbox/ instead, so nothing is lost and the admin is told which
happened.
"""
import html
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import APP_URL, OUTBOX_DIR, SMTP


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
    lines.append("Promotion & Reporting")
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
<tr><td style="padding:20px 28px;border-bottom:1px solid #e6e9ef;font-weight:800;font-size:15px">Promotion &amp; Reporting
<span style="display:block;font-size:11px;letter-spacing:.08em;color:#64748b;font-weight:700">STAFF PLATFORM</span></td></tr>
<tr><td style="padding:26px 28px 24px;font-size:15px;line-height:1.55">
<h1 style="font-size:21px;margin:0 0 16px">{e(mail["heading"])}</h1>
<p style="margin:0 0 14px">{e(mail["greeting"])}</p>{paragraphs}{details}{button}{note}
</td></tr></table>
<p style="color:#94a3b8;font-size:12px;margin:14px 0 0">Sent automatically by the Promotion &amp; Reporting platform.</p>
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
    """Send one email (or save it in the outbox). Returns what happened, in words the admin can read."""
    message = build(to, mail)
    if is_configured():
        try:
            with smtplib.SMTP(SMTP["host"], SMTP["port"], timeout=20) as server:
                server.starttls()
                server.login(SMTP["user"], SMTP["password"])
                server.send_message(message)
            return {"sent": True, "detail": f"Emailed to {to}."}
        except (smtplib.SMTPException, OSError) as error:
            reason = ("the mail server refused the username or app password" if isinstance(error, smtplib.SMTPAuthenticationError)
                      else f"the mail server couldn't be reached ({error.__class__.__name__})")
            return {"sent": False, "detail": f"Not sent: {reason}. Saved to {_save(message)} instead."}
    return {"sent": False, "detail": f"No mail server is set up, so the email was saved to {_save(message)}."}


def send_to_many(recipients: list[str], mail: dict) -> None:
    """Send the same email to several people (used for alerts to HR); each gets their own copy."""
    for to in recipients:
        send(to, mail)


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
