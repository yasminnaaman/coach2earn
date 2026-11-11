"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator, model_validator

from app.models.enums import AccountStatus, GuardianConsentStatus, UserRole


def normalize_email(value: str) -> str:
    """Apply one canonical case-insensitive form before storing or querying."""
    return str(value).strip().lower()


def is_under_18(date_of_birth: date, *, today: date | None = None) -> bool:
    current = today or date.today()
    age = current.year - date_of_birth.year
    if (current.month, current.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age < 18


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
    date_of_birth: date
    guardian_name: str | None = Field(default=None, min_length=1, max_length=200)
    guardian_email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: SecretStr) -> SecretStr:
        return validate_password_length(value)

    @model_validator(mode="after")
    def validate_age_and_guardian(self) -> RegisterRequest:
        today = date.today()
        if self.date_of_birth > today:
            raise ValueError("Date of birth cannot be in the future")
        minor = is_under_18(self.date_of_birth, today=today)
        if minor and (not self.guardian_name or not self.guardian_email):
            raise ValueError("Guardian name and email are required for players under 18")
        if not minor and (self.guardian_name is not None or self.guardian_email is not None):
            raise ValueError("Guardian details are accepted only for players under 18")
        return self


class LoginRequest(AuthRequest):
    pass


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    account_status: AccountStatus
    created_at: datetime
    guardian_consent_status: GuardianConsentStatus | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class CoachPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: str | None = Field(default=None, max_length=2000)


class CoachVerificationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "needs_more_evidence"]
    review_notes: str | None = Field(default=None, max_length=2000)


class GuardianConsentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["verified", "rejected"]
    evidence_reference: str = Field(min_length=1, max_length=2048)
    review_notes: str | None = Field(default=None, max_length=2000)


class AgeVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_birth: date
    guardian_name: str | None = Field(default=None, min_length=1, max_length=200)
    guardian_email: EmailStr | None = None


class GuardianConsentResubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guardian_name: str = Field(min_length=1, max_length=200)
    guardian_email: EmailStr
