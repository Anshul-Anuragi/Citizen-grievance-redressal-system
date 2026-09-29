import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from app.models.user import UserRole

# ---------------------------------------------------------------------------
# Password policy helpers
# ---------------------------------------------------------------------------

_PASSWORD_POLICY_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;\'\/`~]).{8,128}$'
)

_PASSWORD_POLICY_HINT = (
    "Password must be 8–128 characters and contain at least one uppercase letter, "
    "one lowercase letter, one digit, and one special character "
    "(!@#$%^&*(),.?\":{}|<>-_=+[]\\;'/`~)."
)


def validate_password_strength(password: str) -> str:
    """Shared validator callable — raises ValueError on policy violation."""
    if not _PASSWORD_POLICY_PATTERN.match(password):
        raise ValueError(_PASSWORD_POLICY_HINT)
    return password


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    mobile: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """
    Clients may optionally supply the refresh token to revoke.
    If omitted, the server attempts to revoke the token stored in the
    Authorization header context (access token subject lookup).
    """
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    mobile: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    district_code: Optional[str] = None
    department_id: Optional[str] = None
    officer_id: Optional[str] = None


TokenResponse.model_rebuild()
