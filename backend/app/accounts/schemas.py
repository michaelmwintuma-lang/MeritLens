"""Shapes of the data that goes in and out of the account endpoints (validated by Pydantic)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import ALL_ROLES


class UserOut(BaseModel):
    """A user as the API shows it. The password hash is never included."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None
    role: str
    is_active: bool
    must_change_password: bool
    employee_id: int | None
    phone: str | None = None
    job_title: str | None = None
    photo: str | None = None
    can_view_employees: bool | None = False
    email_mode: str | None = "instant"
    totp_enabled: bool | None = False
    guide_done: bool | None = False
    must_set_up_2fa: bool = False
    created_at: datetime | None = None


class LoginIn(BaseModel):
    username: str
    password: str
    code: str | None = None  # the six-digit code, for accounts with two-factor sign-in


class LoginOut(BaseModel):
    # For API clients only. The website gets None: its sign-in travels in an httpOnly cookie that scripts can't read.
    access_token: str | None = None
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


USERNAME = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
EMAIL = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CreateUserIn(BaseModel):
    """What an admin fills in to create an account. The welcome email goes to `email`."""
    username: str = USERNAME
    full_name: str = Field(min_length=2, max_length=120)
    email: str = EMAIL
    role: str = Field(pattern="^(" + "|".join(ALL_ROLES) + ")$")
    job_title: str | None = Field(default=None, max_length=120)
    employee_id: int | None = None


class CreateUserOut(BaseModel):
    """The account, its temporary password (shown to the admin once, stored only as a hash), and the email result."""
    user: UserOut
    temporary_password: str
    email_sent: bool
    email_detail: str


class EditUserIn(BaseModel):
    """What an admin may change about an account. Anything left out stays as it is."""
    username: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    job_title: str | None = Field(default=None, max_length=120)  # an empty text clears it


class ChangeUsernameIn(BaseModel):
    current_password: str
    new_username: str = USERNAME


class SetActiveIn(BaseModel):
    is_active: bool


class ProfileIn(BaseModel):
    """What people may change about themselves. Anything left out stays as it is; an empty phone or title clears it."""
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[0-9+()\-. ]*$")
    job_title: str | None = Field(default=None, max_length=120)


class PhotoIn(BaseModel):
    """A small profile picture as a data URL (the browser shrinks it first), or null to remove it."""
    photo: str | None = Field(default=None, max_length=300_000, pattern=r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$")


class PermissionIn(BaseModel):
    can_view_employees: bool

