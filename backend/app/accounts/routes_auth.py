"""Sign in, see who you are, update your profile, change your password or username."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.schemas import ChangePasswordIn, ChangeUsernameIn, LoginIn, LoginOut, PhotoIn, ProfileIn, UserOut
from app.core.roles import MANAGER
from app.promotion.models import Employee
from app.core.database import get_db
from app.core.security import create_token, get_current_user, hash_password, verify_password
from app.core.activity import record
from app.core import email_templates as templates
from app.core import mailer

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    """Check the username and password and return a login token."""
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    # The same message for an unknown username and a wrong password, so usernames can't be guessed
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        if user is not None:  # a wrong password on a real account is worth knowing about
            record(db, user, "sign_in_failed")
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password.")
    record(db, user, "sign_in")
    db.commit()
    return LoginOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The signed-in user's own account."""
    return user


@router.post("/change-password", response_model=UserOut)
def change_password(body: ChangePasswordIn, background: BackgroundTasks, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Replace your password. You must know the current one."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is wrong.")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    record(db, user, "password_changed")
    db.commit()
    if user.email:  # a security alert, so the person notices if it wasn't them
        background.add_task(mailer.send, user.email, templates.password_changed(user.full_name))
    return user


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


@router.put("/profile/photo", response_model=UserOut)
def set_photo(body: PhotoIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Set or remove your profile picture (a small image, already shrunk by the browser)."""
    user.photo = body.photo
    record(db, user, "profile_updated", "photo" if body.photo else "photo removed")
    db.commit()
    return user
