"""Sign in, see who you are, update your profile, change your password or username."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.schemas import ChangePasswordIn, ChangeUsernameIn, LoginIn, LoginOut, PhotoIn, ProfileIn, UserOut
from app.core.roles import MANAGER
from app.promotion.models import Employee
from app.core.database import get_db
from app.core.security import (CSRF_HEADER, CSRF_VALUE, LOCK_MINUTES, MAX_FAILED_LOGINS, clear_session_cookie,
                               create_token, get_current_user, hash_password, set_session_cookie, verify_password,
                               withdraw_tokens)
from app.core.activity import record
from app.core import email_templates as templates
from app.core import mailer

router = APIRouter(prefix="/api/auth", tags=["auth"])


# One message for every failed sign-in (unknown username, wrong password, locked account), so nobody can tell
# whether an account exists or is locked
SIGN_IN_FAILED = (f"Wrong username or password. After {MAX_FAILED_LOGINS} wrong attempts in a row, an account is "
                  f"locked for {LOCK_MINUTES} minutes.")
_DUMMY_HASH = hash_password("not-a-real-password")


def signed_in(request: Request, response: Response, user: User) -> LoginOut:
    """
    Start a session: the token goes into the httpOnly session cookie. The website (which sends X-Requested-With)
    never sees the token itself; API clients get it in the answer, to send as "Authorization: Bearer".
    """
    token = create_token(user)
    set_session_cookie(response, token)
    from_website = request.headers.get(CSRF_HEADER) == CSRF_VALUE
    return LoginOut(access_token=None if from_website else token, user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Check the username and password and start a session. After MAX_FAILED_LOGINS wrong passwords in a row, the
    account is locked for LOCK_MINUTES: even the right password is refused until then.
    """
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user is None:
        verify_password(body.password, _DUMMY_HASH)  # take as long as a real check
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_FAILED)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_FAILED)
    if not user.is_active or not verify_password(body.password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        record(db, user, "sign_in_failed")  # a wrong password on a real account is worth knowing about
        if user.failed_logins >= MAX_FAILED_LOGINS:
            user.locked_until, user.failed_logins = now + timedelta(minutes=LOCK_MINUTES), 0
            record(db, user, "account_locked")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_FAILED)
    user.failed_logins, user.locked_until = 0, None
    record(db, user, "sign_in")
    db.commit()
    return signed_in(request, response, user)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sign out everywhere: every login token this account has stops working, and this browser's cookie is removed."""
    withdraw_tokens(user)
    db.commit()
    clear_session_cookie(response)
    return {"signed_out": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The signed-in user's own account."""
    return user


@router.post("/change-password", response_model=LoginOut)
def change_password(body: ChangePasswordIn, background: BackgroundTasks, request: Request, response: Response,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Replace your password. You must know the current one. Every other device is signed out; this one gets a new
    session.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is wrong.")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    withdraw_tokens(user)  # signed out everywhere else; this device gets a fresh token below
    record(db, user, "password_changed")
    db.commit()
    if user.email:  # a security alert, so the person notices if it wasn't them
        background.add_task(mailer.send, user.email, templates.password_changed(user.full_name))
    return signed_in(request, response, user)


@router.post("/change-username", response_model=UserOut)
def change_username(body: ChangeUsernameIn, background: BackgroundTasks, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Choose a different username. You must confirm with your current password."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is wrong.")
    new = body.new_username.strip().lower()
    if db.scalar(select(User).where(User.username == new, User.id != user.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")
    record(db, user, "username_changed", f"{user.username} → {new}")
    if user.email:
        background.add_task(mailer.send, user.email, templates.username_changed(user.full_name, user.username, new, by_admin=False))
    user.username = new
    db.commit()
    return user


# ─── My profile ───────────────────────────────────────────────────────────────
@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your account and your work details (read-only): department, manager and, for managers, team size."""
    work = {}
    if user.employee_id and (employee := db.get(Employee, user.employee_id)):
        manager = db.get(User, employee.manager_user_id) if employee.manager_user_id else None
        work = {"employee_id": employee.id, "department": employee.department,
                "manager": manager.full_name if manager else None}
    if user.role == MANAGER:
        work["team_size"] = len(db.scalars(select(Employee).where(Employee.manager_user_id == user.id)).all())
    return {"account": UserOut.model_validate(user), "work": work}


@router.patch("/profile", response_model=UserOut)
def update_profile(body: ProfileIn, background: BackgroundTasks, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Change your name, email, phone or job title. A new email address triggers an alert to the old one."""
    changed = []
    if body.full_name and body.full_name.strip() != user.full_name:
        user.full_name = body.full_name.strip()
        changed.append("name")
    if body.email and body.email.strip().lower() != (user.email or ""):
        new = body.email.strip().lower()
        if db.scalar(select(User).where(User.email == new, User.id != user.id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Another account already uses that email address.")
        if user.email:  # tell the OLD address, so a stolen account can't quietly redirect its emails
            background.add_task(mailer.send, user.email, templates.email_changed(user.full_name, user.email, new))
        user.email = new
        changed.append("email")
    for field in ("phone", "job_title"):
        value = getattr(body, field)
        if value is not None and (value.strip() or None) != getattr(user, field):
            setattr(user, field, value.strip() or None)
            changed.append(field.replace("_", " "))
    if changed:
        record(db, user, "profile_updated", ", ".join(changed))
        db.commit()
    return user


class PreferencesIn(BaseModel):
    email_mode: str = Field(pattern="^(instant|daily)$")


@router.put("/preferences", response_model=UserOut)
def set_preferences(body: PreferencesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """How routine emails arrive: each as it happens, or one digest each morning. Account emails always come at once."""
    user.email_mode = body.email_mode
    record(db, user, "profile_updated", f"emails: {'one a day' if body.email_mode == 'daily' else 'as they happen'}")
    db.commit()
    return user


@router.put("/profile/photo", response_model=UserOut)
def set_photo(body: PhotoIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Set or remove your profile picture (a small image, already shrunk by the browser)."""
    user.photo = body.photo
    record(db, user, "profile_updated", "photo" if body.photo else "photo removed")
    db.commit()
    return user
