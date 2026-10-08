"""Account management. Only administrators can create accounts (for any role) and edit them."""
from email import message_from_bytes
from email.policy import default as default_policy

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.contacts import notify_new_team_members
from app.accounts.schemas import CreateUserIn, CreateUserOut, EditUserIn, PermissionIn, SetActiveIn, UserOut
from app.core.config import OUTBOX_DIR, SMTP
from app.core.database import get_db
from app.core.roles import ADMIN, AUDITOR, FINANCE, HR, MANAGER
from app.core.security import hash_password, require_roles, temporary_password, withdraw_tokens
from app.core import email_templates as templates
from app.core import mailer
from app.core.activity import ACTIONS, ActivityEntry, record
from app.promotion.models import Decision, Employee, Nomination

router = APIRouter(prefix="/api/admin/users", tags=["admin"])
employees_router = APIRouter(prefix="/api/admin/employees", tags=["admin"])
admin_only = require_roles(ADMIN)
STAFF_ROLES = (ADMIN, HR, FINANCE, AUDITOR)  # "Administration" accounts: not linked to an employee record


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Every account, sorted by name."""
    return db.scalars(select(User).order_by(User.full_name)).all()


def check_unique(db: Session, username: str | None = None, email: str | None = None, except_id: int | None = None):
    """Usernames and email addresses can belong to one account only."""
    if username and db.scalar(select(User).where(User.username == username, User.id != except_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")
    if email and db.scalar(select(User).where(User.email == email, User.id != except_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Another account already uses that email address.")


@router.post("", response_model=CreateUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUserIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """
    Create an account with a temporary password and send the welcome email with the sign-in details. The person
    must choose their own password at first sign-in (and may change their username then).
    """
    username = body.username.strip().lower()
    email = body.email.strip().lower()
    check_unique(db, username=username, email=email)
    if body.employee_id is not None and body.role in STAFF_ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Administration accounts (Admin, HR, Finance and "
                            "Auditor) aren't linked to an employee record. Create an Employee or Manager account for that.")
    if body.employee_id is not None:
        if db.get(Employee, body.employee_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "There is no employee with that number.")
        if db.scalar(select(User).where(User.employee_id == body.employee_id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "That employee record already has a login.")

    password = temporary_password()
    user = User(
        username=username,
        full_name=body.full_name.strip(),
        email=email,
        role=body.role,
        job_title=(body.job_title or "").strip() or None,
        password_hash=hash_password(password),
        must_change_password=True,
        employee_id=body.employee_id,
    )
    db.add(user)
    record(db, admin, "account_created", f"{username} ({body.role})")
    db.commit()
    result = mailer.send(email, templates.welcome(user.full_name, username, password, user.job_title))
    return CreateUserOut(user=UserOut.model_validate(user), temporary_password=password,
                         email_sent=result["sent"], email_detail=result["detail"])


@router.patch("/{user_id}", response_model=UserOut)
def edit_user(user_id: int, body: EditUserIn, background: BackgroundTasks, db: Session = Depends(get_db),
              admin: User = Depends(admin_only)):
    """Change an account's username, name or email address. The person signs in with the new username."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    username = body.username.strip().lower() if body.username else None
    email = body.email.strip().lower() if body.email else None
    check_unique(db, username=username, email=email, except_id=user.id)
    if username and username != user.username:
        if user.email:  # a security alert, so the person knows how to sign in now
            background.add_task(mailer.send, user.email, templates.username_changed(user.full_name, user.username, username, by_admin=True))
        user.username = username
    if email:
        user.email = email
    if body.full_name:
        user.full_name = body.full_name.strip()
    if body.job_title is not None:
        user.job_title = body.job_title.strip() or None
    record(db, admin, "account_edited", user.username)
    db.commit()
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
def set_active(user_id: int, body: SetActiveIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Deactivate an account (the person can no longer sign in) or reactivate it."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    if user.id == admin.id and not body.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't deactivate your own account.")
    user.is_active = body.is_active
    record(db, admin, "account_reactivated" if body.is_active else "account_deactivated", user.username)
    db.commit()
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """
    Delete an account for good. Not allowed for your own account, or for an account that appears in the decision
    log (it recommended someone or decided on a promotion): deleting it would erase who made those decisions, so
    deactivate it instead. A manager's team members stay in the directory, without a manager. Activity-log
    entries keep the person's name.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't delete your own account.")
    if db.scalar(select(Nomination.id).where(Nomination.nominated_by == user.id).limit(1)) or \
            db.scalar(select(Decision.id).where(Decision.decided_by == user.id).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{user.full_name} appears in the promotion decision log, which must keep "
                            "who recommended and decided. Deactivate the account instead: they can no longer sign in.")
    db.execute(update(Employee).where(Employee.manager_user_id == user.id).values(manager_user_id=None))
    db.execute(update(ActivityEntry).where(ActivityEntry.user_id == user.id).values(user_id=None))
    record(db, admin, "account_deleted", f"{user.username} ({user.role})")
    db.delete(user)
    db.commit()
    return {"deleted": user_id}


@router.patch("/{user_id}/permissions", response_model=UserOut)
def set_permissions(user_id: int, body: PermissionIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """
    Let an Admin account view employees' records and scores (read-only), or stop it. Only Admin accounts can be
    given this: HR already sees everyone, and employees and managers see what their role allows.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    if user.role != ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only Admin accounts can be given this permission.")
    user.can_view_employees = body.can_view_employees
    record(db, admin, "permission_changed", f"{user.username}: employee data {'on' if body.can_view_employees else 'off'}")
    db.commit()
    return user


@router.post("/{user_id}/reset-password", response_model=CreateUserOut)
def reset_password(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Give a user a new temporary password, e.g. when they have forgotten theirs. It is emailed to them too."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such account.")
    password = temporary_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    user.failed_logins, user.locked_until = 0, None  # a reset also unlocks the account
    withdraw_tokens(user)                            # and signs the person out everywhere
    record(db, admin, "password_reset", user.username)
    db.commit()
    if user.email:
        result = mailer.send(user.email, templates.password_reset(user.full_name, user.username, password))
    else:
        result = {"sent": False, "detail": "This account has no email address, so give the password to the person yourself."}
    return CreateUserOut(user=UserOut.model_validate(user), temporary_password=password,
                         email_sent=result["sent"], email_detail=result["detail"])


# ─── Managers' teams ──────────────────────────────────────────────────────────
@employees_router.get("")
def list_employees_for_admin(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """
    The employee directory as the admin needs it to link logins and build teams: names, departments, managers.
    No scores or work records: admins manage accounts, not promotions.
    """
    linked = {u.employee_id: u.username for u in db.scalars(select(User).where(User.employee_id.is_not(None)))}
    return [{"id": e.id, "full_name": e.full_name, "department": e.department, "manager_user_id": e.manager_user_id,
             "login": linked.get(e.id)} for e in db.scalars(select(Employee).order_by(Employee.full_name))]


class TeamIn(BaseModel):
    employee_ids: list[int]


@router.put("/{user_id}/team")
def set_team(user_id: int, body: TeamIn, background: BackgroundTasks, db: Session = Depends(get_db),
             admin: User = Depends(admin_only)):
    """
    Make exactly these employees the manager's team. People removed from the list no longer have a manager
    until they are given one; people on someone else's team move to this manager.
    """
    manager = db.get(User, user_id)
    if manager is None or manager.role != MANAGER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Teams can only be given to manager accounts.")
    wanted = set(body.employee_ids)
    found = {e.id: e for e in db.scalars(select(Employee).where(Employee.id.in_(wanted)))}
    if missing := wanted - set(found):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No employee with number(s): {', '.join(map(str, sorted(missing)))}.")
    for employee in db.scalars(select(Employee).where(Employee.manager_user_id == manager.id)):
        if employee.id not in wanted:
            employee.manager_user_id = None
    joined = [e.full_name for e in found.values() if e.manager_user_id != manager.id]
    for employee in found.values():
        employee.manager_user_id = manager.id
    record(db, admin, "team_set", f"{manager.username}: {len(wanted)} people")
    db.commit()
    notify_new_team_members(background, db, {manager.id: sorted(joined)})  # only the people new to the team
    return {"manager": manager.username, "team_size": len(wanted)}


# ─── Activity log ─────────────────────────────────────────────────────────────
activity_router = APIRouter(prefix="/api/admin/activity", tags=["admin"])


@activity_router.get("")
def activity_log(action: str | None = None, search: str = "", db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """The latest 500 entries, newest first; filter by action, or search names and details."""
    query = select(ActivityEntry).order_by(ActivityEntry.on_date.desc(), ActivityEntry.id.desc())
    if action:
        query = query.where(ActivityEntry.action == action)
    if search.strip():
        like = f"%{search.strip()}%"
        query = query.where(ActivityEntry.user_name.ilike(like) | ActivityEntry.details.ilike(like))
    entries = db.scalars(query.limit(500))
    return {
        "actions": ACTIONS,
        "entries": [{"id": e.id, "date": e.on_date.isoformat(), "user": e.user_name, "action": e.action,
                     "action_label": ACTIONS[e.action], "details": e.details} for e in entries],
    }


# ─── Email: status, test email, and the outbox ────────────────────────────────
email_router = APIRouter(prefix="/api/admin/email", tags=["admin"])


@email_router.get("")
def email_status(_: User = Depends(admin_only)):
    """Whether a mail server is set up (never the password itself), and how many emails are in the outbox."""
    outbox = sorted(OUTBOX_DIR.glob("*.eml")) if OUTBOX_DIR.exists() else []
    return {"configured": mailer.is_configured(), "host": SMTP["host"] or None, "port": SMTP["port"],
            "sender": SMTP["sender"] if mailer.is_configured() else None, "outbox_count": len(outbox)}


class TestEmailIn(BaseModel):
    to: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@email_router.post("/test")
def send_test_email(body: TestEmailIn, admin: User = Depends(admin_only)):
    """Send a test email, to check the settings work. Waits for the answer, so the admin sees any problem."""
    return mailer.send(body.to.strip(), templates.test_email(admin.full_name))


@email_router.get("/outbox")
def outbox(_: User = Depends(admin_only)):
    """The 30 most recent saved (not sent) emails: who to, the subject and the plain-text body."""
    if not OUTBOX_DIR.exists():
        return []
    items = []
    for path in sorted(OUTBOX_DIR.glob("*.eml"), reverse=True)[:30]:
        message = message_from_bytes(path.read_bytes(), policy=default_policy)
        items.append({"file": path.name, "to": message["To"], "subject": message["Subject"],
                      "body": message.get_body(("plain",)).get_content()})
    return items
