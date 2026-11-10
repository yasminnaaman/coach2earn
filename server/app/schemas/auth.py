"""Authentication request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.models.enums import AccountStatus, UserRole


def normalize_email(value: str) -> str:
    """Apply one canonical case-insensitive form before storing or querying."""
    return str(value).strip().lower()


def validate_password_length(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    if not 12 <= len(password) <= 128:
        raise ValueError("Password must contain between 12 and 128 characters")
    return value


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email_field(cls, value: str) -> str:
        return normalize_email(value)


class RegisterRequest(AuthRequest):
    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: SecretStr) -> SecretStr:
        return validate_password_length(value)


class LoginRequest(AuthRequest):
    pass


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    account_status: AccountStatus
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class CoachPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: str | None = Field(default=None, max_length=2000)
