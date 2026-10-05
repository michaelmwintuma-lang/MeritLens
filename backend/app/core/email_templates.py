"""
The text of every email the platform sends, in one place. Each function returns the parts of one email; mailer.py
turns them into the HTML and plain-text versions.

Rule for anything about anonymous reports: never the report's text, and nothing about who sent it.
"""
from app.core.mailer import link

FIRST_SIGN_IN = "When you first sign in, you'll be asked to choose your own password. You can change your username then too."


def welcome(full_name: str, username: str, temporary_password: str, job_title: str | None = None) -> dict:
    return {
        "subject": "Your account for the Promotion & Reporting platform",
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
        "heading": "Your password was changed",
        "greeting": f"Hello {full_name},",
        "paragraphs": ["The password for your account has just been changed."],
        "note": "If this was you, there's nothing to do. If it wasn't, ask your administrator to reset your password at once.",
    }


def username_changed(full_name: str, old: str, new: str, by_admin: bool) -> dict:
    return {
        "subject": "Your username was changed",
        "heading": "Your username was changed",
        "greeting": f"Hello {full_name},",
        "paragraphs": [f"{'An administrator changed' if by_admin else 'You changed'} the username you sign in with."],
        "details": [("Old username", old), ("New username", new)],
        "button": ("Sign in", link("/login")),
        "note": "If you didn't expect this, tell your administrator straight away.",
    }


def nomination_received(hr_name: str, employee_name: str, manager_name: str, title: str | None = None) -> dict:
    return {
        "subject": f"New nomination: {employee_name}",
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
        "heading": f"Promotion {'approved' if approved else 'not approved'}",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"HR has decided on your nomination of {employee_name}."],
        "details": details,
        "button": ("See your nominations", link("/nominations")),
    }


def promotion_approved(employee_name: str, title: str | None = None, start: str | None = None,
                       raise_percent: float | None = None) -> dict:
    details = [(label, value) for label, value in [("New role", title), ("Starting", start),
               ("Pay rise", f"{raise_percent:g}%" if raise_percent is not None else None)] if value]
    return {
        "subject": "Your promotion has been approved",
        "heading": "Congratulations!",
        "greeting": f"Hello {employee_name},",
        "paragraphs": ["Your manager nominated you for promotion, and HR has approved it. Your manager and HR will be in touch about the next steps."],
        "details": details,
        "button": ("Sign in", link("/login")),
    }


# Priorities are stored as low, medium and high; the middle one is called "moderate" wherever people read it
PRIORITY_WORDS = {"low": "low", "medium": "moderate", "high": "high"}


def report_alert(hr_name: str, case_id: str, category: str, priority: str) -> dict:
    """A new anonymous report. Only the case ID, category and priority: never the text or anything about the reporter."""
    return {
        "subject": f"New anonymous report ({PRIORITY_WORDS.get(priority, priority)} priority)",
        "heading": "A new anonymous report is waiting",
        "greeting": f"Hello {hr_name},",
        "paragraphs": ["A new report has arrived through the anonymous reporting channel. For the reporter's protection, "
                       "this email doesn't include what it says: please read it in the report inbox."],
        "details": [("Case", case_id), ("Category", category), ("Priority", PRIORITY_WORDS.get(priority, priority).capitalize())],
        "button": ("Open the report inbox", link(f"/reports/{case_id}")),
    }


def test_email(name: str) -> dict:
    return {
        "subject": "Test email from the Promotion & Reporting platform",
        "heading": "Email is working",
        "greeting": f"Hello {name},",
        "paragraphs": ["This is a test email sent from the admin's Email page. If you can read it, emails from the platform will arrive."],
        "button": ("Open the platform", link("/")),
    }


def demo_request(name: str, email: str, organisation: str, job_title: str, size: str, interest: str, message: str) -> dict:
    """Someone asked for a demo on the public website. Replying to this email answers them directly."""
    return {
        "subject": f"Demo request: {organisation}",
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
        "heading": "New on your team",
        "greeting": f"Hello {manager_name},",
        "paragraphs": [f"{'These people are' if many else 'This person is'} now registered under you as their manager. "
                       "You can see their readiness on My team."],
        "details": [("Team member" if not many else f"Member {i + 1}", name) for i, name in enumerate(names[:20])]
                   + ([("And", f"{len(names) - 20} more")] if len(names) > 20 else []),
        "button": ("Open My team", link("/team")),
    }

