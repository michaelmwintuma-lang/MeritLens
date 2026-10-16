"""
The text of every email the platform sends, in one place. Each function returns the parts of one email; mailer.py
turns them into the HTML and plain-text versions.

Two optional parts decide how an email is handled (mailer.py):
- "kind": "security" for emails about someone's account (sign-in details, password, username, email address).
  These always go out at once, whatever the person chose. Everything else is "routine" and can wait for a daily
  digest if the person prefers that.
- "notice": the line shown in the recipient's notification bell, when the email is about something they may need to
  act on. The bell and the email then come from the same event and never disagree.
"""
from app.core.config import APP_NAME
from app.core.mailer import link

FIRST_SIGN_IN = "When you first sign in, you'll be asked to choose your own password. You can change your username then too."


def welcome(full_name: str, username: str, temporary_password: str, job_title: str | None = None) -> dict:
    return {
        "subject": f"Your {APP_NAME} account",
        "kind": "security",
        "heading": "Welcome aboard",
        "greeting": f"Hello {full_name},",
        "paragraphs": [f"An administrator has created an account for you{f' as {job_title}' if job_title else ''}. Here are your sign-in details.", FIRST_SIGN_IN],
        "details": [("Username", username), ("Temporary password", temporary_password)],
        "button": ("Sign in", link("/login")),
        "note": "For your security, please delete this email once you've signed in. If you weren't expecting it, tell your HR department.",
    }


def password_reset(full_name: str, username: str, temporary_password: str) -> dict:
    return {
        "subject": "Your new temporary password",
        "kind": "security",
        "heading": "Your password was reset",
        "greeting": f"Hello {full_name},",
        "paragraphs": ["An administrator has given you a new temporary password. Your old password no longer works.", FIRST_SIGN_IN],
        "details": [("Username", username), ("Temporary password", temporary_password)],
        "button": ("Sign in", link("/login")),
        "note": "If you didn't ask for this, tell your administrator straight away.",
    }


def password_changed(full_name: str) -> dict:
    return {
        "subject": "Your password was changed",
        "kind": "security",
        "heading": "Your password was changed",
        "greeting": f"Hello {full_name},",
        "paragraphs": ["The password for your account has just been changed."],
        "note": "If this was you, there's nothing to do. If it wasn't, ask your administrator to reset your password at once.",
    }


def username_changed(full_name: str, old: str, new: str, by_admin: bool) -> dict:
    return {
        "subject": "Your username was changed",
        "kind": "security",
        "heading": "Your username was changed",
        "greeting": f"Hello {full_name},",
        "paragraphs": [f"{'An administrator changed' if by_admin else 'You changed'} the username you sign in with."],
        "details": [("Old username", old), ("New username", new)],
        "button": ("Sign in", link("/login")),
        "note": "If you didn't expect this, tell your administrator straight away.",
    }


def two_factor_off(full_name: str) -> dict:
    return {
        "subject": "Two-factor sign-in was turned off",
        "kind": "security",
        "heading": "Two-factor sign-in was turned off",
        "greeting": f"Hello {full_name},",
        "paragraphs": ["Two-factor sign-in has just been turned off for your account, so signing in now needs only your password."],
        "button": ("Open my profile", link("/account")),
        "note": "If this wasn't you, change your password and tell your administrator straight away.",
    }


def nomination_received(hr_name: str, employee_name: str, manager_name: str, title: str | None = None) -> dict:
    return {
        "subject": f"New nomination: {employee_name}",
        "notice": f"New nomination to review: {employee_name}",
        "heading": "A nomination is waiting for review",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"{manager_name} has nominated {employee_name} for promotion"
                       + (f" to {title}" if title else "") + ". You'll see the manager's recommendation next to the model's view."],
        "button": ("Review nominations", link("/nominations")),
    }


def decision_for_manager(manager_name: str, employee_name: str, approved: bool, reason: str | None,
                         title: str | None = None, raise_percent: float | None = None) -> dict:
    details = [("Employee", employee_name), ("Decision", "Approved" if approved else "Not approved")]
    if approved and title:
        details.append(("New role", title))
    if approved and raise_percent is not None:
        details.append(("Pay rise", f"{raise_percent:g}%"))
    if reason:
        details.append(("HR's reason", reason))
    return {
        "subject": f"Decision on your nomination of {employee_name}",
        "notice": f"Promotion {'approved' if approved else 'not approved'}: {employee_name}",
        "heading": f"Promotion {'approved' if approved else 'not approved'}",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"HR has decided on your nomination of {employee_name}"
                       + (", and Finance has confirmed the pay rise." if approved else ".")],
        "details": details,
        "button": ("See your nominations", link("/nominations")),
    }


def promotion_approved(employee_name: str, title: str | None = None, start: str | None = None,
                       raise_percent: float | None = None) -> dict:
    details = [(label, value) for label, value in [("New role", title), ("Starting", start),
               ("Pay rise", f"{raise_percent:g}%" if raise_percent is not None else None)] if value]
    return {
        "subject": "Your promotion has been approved",
        "notice": f"Your promotion{f' to {title}' if title else ''} has been approved",
        "heading": "Congratulations!",
        "greeting": f"Hello {employee_name},",
        "paragraphs": ["Your manager nominated you for promotion, HR has approved it and Finance has confirmed the pay rise. "
                       "Your manager and HR will be in touch about the next steps."],
        "details": details,
        "button": ("Sign in", link("/login")),
    }


def pay_review_waiting(finance_name: str, employee_name: str, title: str | None, raise_percent: float,
                       resubmitted: bool = False) -> dict:
    """To Finance: a promotion pay rise needs signing off."""
    details = [("Employee", employee_name), ("New role", title), ("Pay rise", f"{raise_percent:g}%")]
    return {
        "subject": f"Pay rise to sign off: {employee_name}" + (" (revised)" if resubmitted else ""),
        "notice": f"Pay rise to sign off: {employee_name}" + (" (revised)" if resubmitted else ""),
        "heading": "A promotion pay rise needs your sign-off",
        "greeting": f"Hello {finance_name},",
        "paragraphs": [("HR has revised a pay rise you sent back, and resubmitted it." if resubmitted else
                        "HR has approved a promotion. The pay rise that comes with it needs Finance's sign-off before "
                        "anyone is told.")],
        "details": [(label, value) for label, value in details if value],
        "button": ("Review pay rises", link("/finance")),
    }


def pay_returned(hr_name: str, employee_name: str, finance_name: str, note: str) -> dict:
    """To HR: Finance sent a pay rise back."""
    return {
        "subject": f"Pay rise sent back by Finance: {employee_name}",
        "notice": f"Finance sent back {employee_name}'s pay rise",
        "heading": "Finance has a question about a pay rise",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"{finance_name} sent the pay rise for {employee_name}'s promotion back to HR. Please revise it "
                       "and resubmit it. Nobody has been told about the promotion yet."],
        "details": [("Finance's reason", note)],
        "button": ("Open nominations", link("/nominations")),
    }


def test_email(name: str) -> dict:
    return {
        "subject": f"Test email from {APP_NAME}",
        "heading": "Email is working",
        "greeting": f"Hello {name},",
        "paragraphs": ["This is a test email sent from the admin's Email page. If you can read it, emails from the platform will arrive."],
        "button": ("Open the platform", link("/")),
    }


def demo_request(name: str, email: str, organisation: str, job_title: str, size: str, interest: str, message: str) -> dict:
    """Someone asked for a demo on the public website. Replying to this email answers them directly."""
    return {
        "subject": f"Demo request: {organisation}",
        "notice": f"New demo request: {organisation}",
        "heading": "New demo request",
        "greeting": "Hello,",
        "paragraphs": [f"{name} from {organisation} asked for a demo on the website. Reply to this email to answer them.",
                       *([f"Their message: “{message}”"] if message else [])],
        "details": [("Name", name), ("Email", email), ("Organisation", organisation), ("Job title", job_title or "–"),
                    ("Size", size), ("Interested in", interest)],
        "button": ("See all demo requests", link("/admin/demo-requests")),
        "reply_to": email,
    }


def email_changed(full_name: str, old: str, new: str) -> dict:
    """Sent to the OLD address, so the person notices if someone else changed it."""
    return {
        "subject": "Your email address was changed",
        "kind": "security",
        "heading": "Your email address was changed",
        "greeting": f"Hello {full_name},",
        "paragraphs": [f"The email address on your account was changed from {old} to {new}. Emails from the platform now go to the new address.",
                       "If you didn't make this change, tell your administrator straight away."],
        "button": ("Open my profile", link("/account")),
    }


def team_members_added(manager_name: str, names: list[str]) -> dict:
    """A manager's team grew. Names only: no scores or records."""
    many = len(names) > 1
    return {
        "subject": f"{len(names)} new team members" if many else f"{names[0]} has joined your team",
        "notice": f"{len(names)} people joined your team" if many else f"{names[0]} joined your team",
        "heading": "New on your team",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"{'These people are' if many else 'This person is'} now registered under you as their manager. "
                       "You can see their readiness on My team."],
        "details": [("Team member" if not many else f"Member {i + 1}", name) for i, name in enumerate(names[:20])]
                   + ([("And", f"{len(names) - 20} more")] if len(names) > 20 else []),
        "button": ("Open My team", link("/team")),
    }



def cycle_opened(manager_name: str, cycle_name: str, team: int, recommended: int, nominations_close: str | None) -> dict:
    """A review cycle opened. Totals for the manager's own team only: no names or scores."""
    deadline = f"Nominations close on {nominations_close}." if nominations_close else "There is no nomination deadline."
    return {
        "subject": f"Review cycle open: {cycle_name}",
        "notice": f"Review cycle open: {cycle_name}",
        "heading": "A review cycle has started",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"HR has opened the review cycle “{cycle_name}”. Everyone's readiness has been worked out and "
                       "saved for the cycle, so you can see your team's scores now. The model only advises: you decide "
                       f"whom to recommend. {deadline}"],
        "details": [("Your team", str(team)), ("The model recommends", str(recommended))]
                   + ([("Nominations close", nominations_close)] if nominations_close else []),
        "button": ("Open My team", link("/team")),
    }


def approval_needed(hr_name: str, requester: str, summary: str) -> dict:
    return {
        "subject": f"Your approval is needed: {summary[:80]}",
        "notice": f"{requester} asks for your approval",
        "heading": "A second HR person's approval is needed",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"{requester} has asked for this, and it needs a second HR person before it happens:",
                       summary, "Nothing changes until you approve it."],
        "button": ("Open approvals", link("/approvals")),
    }


def correction_received(hr_name: str, employee_name: str, field: str) -> dict:
    return {
        "subject": f"Record correction requested: {employee_name}",
        "notice": f"Record correction to check: {employee_name}",
        "heading": "A record correction is waiting",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"{employee_name} has asked for a value in their work record to be corrected, with evidence. "
                       "Nothing changes until you confirm it."],
        "details": [("Employee", employee_name), ("Value", field)],
        "button": ("Open the correction queue", link("/corrections")),
    }


def correction_decided(employee_name: str, field: str, confirmed: bool, value: str, reason: str | None) -> dict:
    if confirmed:
        paragraphs = [f"HR checked your evidence and corrected your {field}.",
                      "Your readiness score has been worked out again with the corrected record."]
        details = [("Value", field), ("Corrected to", value)]
    else:
        paragraphs = [f"HR checked your request about your {field} and kept the value in your record as it is."]
        details = [("Value", field), ("HR's reason", reason or "")]
    return {
        "subject": f"Your record correction: {'corrected' if confirmed else 'not changed'}",
        "notice": "HR corrected your record" if confirmed else "HR decided on your correction request",
        "heading": "HR has decided on your record correction",
        "greeting": f"Hello {employee_name},",
        "paragraphs": paragraphs,
        "details": details,
        "button": ("See my growth", link("/my-readiness")),
    }


# ─── Reminders (app/core/reminders.py sends each one once) ──────────────────
def reminder_nominations(manager_name: str, cycle_name: str, waiting: int, nominations_close: str, days_left: int) -> dict:
    """A manager, shortly before a cycle's nomination deadline. A count only: no names or scores."""
    when = "today" if days_left == 0 else "tomorrow" if days_left == 1 else f"in {days_left} days"
    return {
        "subject": f"Nominations close {when}: {cycle_name}",
        "notice": f"Nominations for {cycle_name} close {when}",
        "heading": "A reminder before nominations close",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"Nominations for the review cycle “{cycle_name}” close {when} ({nominations_close}). The model "
                       f"recommends {waiting} member{'' if waiting == 1 else 's'} of your team you haven't nominated. "
                       "The model only advises: you decide whom to recommend, and it's fine to recommend no one."],
        "button": ("Open My team", link("/team")),
    }


def reminder_pay_waiting(finance_name: str, names: list[str]) -> dict:
    """Finance: pay rises waiting more than two working days."""
    many = len(names) > 1
    return {
        "subject": f"{len(names)} pay rises waiting for sign-off" if many else f"Pay rise waiting for sign-off: {names[0]}",
        "notice": f"{len(names)} pay rises waiting more than 2 working days" if many else f"Pay rise waiting: {names[0]}",
        "heading": "Pay rises are waiting for you",
        "greeting": f"Hello {finance_name},",
        "paragraphs": ["These promotion pay rises have waited more than two working days. Nobody is told about the "
                       "promotion until you sign it off, or send it back to HR."],
        "details": [("Employee" if not many else f"Pay rise {i + 1}", name) for i, name in enumerate(names[:20])],
        "button": ("Review pay rises", link("/finance")),
    }


def reminder_cycle_ready(hr_name: str, cycle_name: str) -> dict:
    """HR: a cycle's nominations have closed and every one is decided."""
    return {
        "subject": f"Ready to close: {cycle_name}",
        "notice": f"{cycle_name} is ready to close",
        "heading": "A review cycle is ready to close",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"Nominations for “{cycle_name}” have closed, and every nomination in it is decided. Close the cycle "
                       "to keep its scores as they are and to allow a new model to be released."],
        "button": ("Open review cycles", link("/cycles")),
    }


def reminder_corrections_waiting(hr_name: str, count: int) -> dict:
    """HR: record corrections waiting more than three days. A count only."""
    return {
        "subject": f"{count} record correction{'s' if count != 1 else ''} waiting",
        "notice": f"{count} record correction{'s' if count != 1 else ''} waiting more than 3 days",
        "heading": "Record corrections are waiting",
        "greeting": f"Hello {hr_name},",
        "paragraphs": [f"{count} employee request{'s' if count != 1 else ''} to correct their record "
                       f"{'have' if count != 1 else 'has'} waited more than three days. The employee is waiting for your answer."],
        "button": ("Open the correction queue", link("/corrections")),
    }

