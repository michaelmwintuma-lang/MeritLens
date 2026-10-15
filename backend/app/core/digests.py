"""
The daily digest: for people who chose "one email a day", the routine emails held since the last digest, gathered
into one email each morning (the scheduler, at DIGEST_HOUR). Account and security emails are never held. Their bell
showed each item as it happened, so a digest is only the email side.
"""
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import mailer
from app.core.config import APP_NAME
from app.core.mailer import EmailLog, link


def digest_email(items: list[dict]) -> dict:
    """One email listing every held email's subject, with a link to each page."""
    details = [(f"{i + 1}.", item["subject"]) for i, item in enumerate(items[:30])]
    if len(items) > 30:
        details.append(("And", f"{len(items) - 30} more"))
    pages = {item["button"][1] for item in items if item.get("button")}
    return {
        "subject": f"Your {APP_NAME} digest: {len(items)} update{'' if len(items) == 1 else 's'}",
        "kind": "digest",
        "heading": "Since your last digest",
        "greeting": "Hello,",
        "paragraphs": [f"Here is what happened since yesterday's digest. You chose one email a day for updates like these; "
                       "you can change that on My profile."],
        "details": details,
        "button": ("Open " + APP_NAME, next(iter(pages)) if len(pages) == 1 else link("/")),
    }


def send_due(db: Session) -> int:
    """Send each person with held emails one digest. Returns how many digests were sent."""
    held: dict[str, list[EmailLog]] = defaultdict(list)
    for entry in db.scalars(select(EmailLog).where(EmailLog.status == "held").order_by(EmailLog.created_at)):
        held[entry.to_address].append(entry)
    for address, entries in held.items():
        mailer.send(address, digest_email([json.loads(e.mail_json) for e in entries]))
        for entry in entries:
            entry.status, entry.mail_json = "in_digest", None
    db.commit()
    return len(held)
