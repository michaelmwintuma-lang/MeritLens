"""Who to email: the people behind accounts, looked up when an email needs sending."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.roles import HR


def hr_contacts(db: Session) -> list[tuple[str, str]]:
    """(email, name) of every active HR account that has an email address."""
    users = db.scalars(select(User).where(User.role == HR, User.is_active.is_(True), User.email.is_not(None)))
    return [(u.email, u.full_name) for u in users]


def login_for_employee(db: Session, employee_id: int) -> User | None:
    """The account linked to an employee record, if there is one."""
    return db.scalar(select(User).where(User.employee_id == employee_id, User.is_active.is_(True)))


def notify_new_team_members(background, db: Session, joined: dict[int, list[str]]) -> None:
    """
    Email each manager the names of people just registered under them. `joined` is {manager's user id: [names]}.
    Sent in the background, so a slow mail server never delays the page.
    """
    from app.core import email_templates as templates
    from app.core import mailer

    for manager_id, names in joined.items():
        manager = db.get(User, manager_id)
        if names and manager and manager.is_active and manager.email:
            background.add_task(mailer.send, manager.email, templates.team_members_added(manager.full_name, names))

