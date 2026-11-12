"""Validated profile, discovery, and qualification API schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.models.enums import VerificationStatus


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SpecialisationRead(BaseModel):
    id: UUID
    category: str
    name: str
    slug: str


class PlayerProfileCreate(RequestModel):
    gaming_experience_years: int | None = Field(default=None, ge=0, le=100)
    skill_level: str | None = Field(default=None, min_length=1, max_length=80)
    interests: list[str] = Field(default_factory=list, max_length=50)
    training_goals: str | None = Field(default=None, max_length=4000)
    coaching_requirements: str | None = Field(default=None, max_length=4000)
    budget_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    game_ids: list[UUID] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_budget_pair(self) -> PlayerProfileCreate:
        if (self.budget_amount is None) != (self.budget_currency is None):
            raise ValueError("budget_amount and budget_currency must be provided together")
        if len(set(self.game_ids)) != len(self.game_ids):
            raise ValueError("game_ids must not contain duplicates")
        return self


class PlayerProfileUpdate(RequestModel):
    gaming_experience_years: int | None = Field(default=None, ge=0, le=100)
    skill_level: str | None = Field(default=None, min_length=1, max_length=80)
    interests: list[str] | None = Field(default=None, max_length=50)
    training_goals: str | None = Field(default=None, max_length=4000)
    coaching_requirements: str | None = Field(default=None, max_length=4000)
    budget_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    game_ids: list[UUID] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_budget_pair_if_touched(self) -> PlayerProfileUpdate:
        supplied = self.model_fields_set
        if {"budget_amount", "budget_currency"} & supplied:
            if not {"budget_amount", "budget_currency"} <= supplied:
                raise ValueError("budget_amount and budget_currency must be updated together")
            if (self.budget_amount is None) != (self.budget_currency is None):
                raise ValueError("budget_amount and budget_currency must be provided together")
        if self.game_ids is not None and len(set(self.game_ids)) != len(self.game_ids):
            raise ValueError("game_ids must not contain duplicates")
        if "interests" in supplied and self.interests is None:
            raise ValueError("interests cannot be null")
        return self


class PlayerProfileRead(BaseModel):
    id: UUID
    gaming_experience_years: int | None
    skill_level: str | None
    interests: list[str]
    training_goals: str | None
    coaching_requirements: str | None
    budget_amount: Decimal | None
    budget_currency: str | None
    games: list[SpecialisationRead]
    created_at: datetime
    updated_at: datetime


class CoachProfileCreate(RequestModel):
    professional_bio: str | None = Field(default=None, max_length=5000)
    coaching_goals: str | None = Field(default=None, max_length=4000)
    experience_years: int = Field(default=0, ge=0, le=100)
    availability: dict[str, Any] = Field(default_factory=dict)
    specialisation_ids: list[UUID] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_specialisations(self) -> CoachProfileCreate:
        if len(set(self.specialisation_ids)) != len(self.specialisation_ids):
            raise ValueError("specialisation_ids must not contain duplicates")
        return self


class CoachProfileUpdate(RequestModel):
    professional_bio: str | None = Field(default=None, max_length=5000)
    coaching_goals: str | None = Field(default=None, max_length=4000)
    experience_years: int | None = Field(default=None, ge=0, le=100)
    availability: dict[str, Any] | None = None
    specialisation_ids: list[UUID] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def unique_specialisations(self) -> CoachProfileUpdate:
        if self.specialisation_ids is not None and len(set(self.specialisation_ids)) != len(
            self.specialisation_ids
        ):
            raise ValueError("specialisation_ids must not contain duplicates")
        if "availability" in self.model_fields_set and self.availability is None:
            raise ValueError("availability cannot be null")
        return self


class CoachProfileRead(BaseModel):
    id: UUID
    professional_bio: str | None
    coaching_goals: str | None
    experience_years: int
    availability: dict[str, Any]
    verification_status: VerificationStatus
    specialisations: list[SpecialisationRead]
    created_at: datetime
    updated_at: datetime


class PublicPackagePrice(BaseModel):
    title: str
    price_per_session: Decimal
    currency: str
    session_limit: int


class PublicCoachRead(BaseModel):
    id: UUID
    name: str = "Coach"
    professional_bio: str
    coaching_goals: str | None
    experience_years: int
    verified: Literal[True] = True
    specialisations: list[SpecialisationRead]
    packages: list[PublicPackagePrice]


class QualificationCreate(RequestModel):
    title: str = Field(min_length=1, max_length=200)
    issuing_organisation: str | None = Field(default=None, max_length=200)
    credential_reference: str | None = Field(default=None, max_length=200)
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    evidence_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> QualificationCreate:
        if self.issued_at and self.expires_at:
            issued_aware = self.issued_at.utcoffset() is not None
            expires_aware = self.expires_at.utcoffset() is not None
            if issued_aware != expires_aware:
                raise ValueError("issued_at and expires_at must both include a timezone or omit one")
            if issued_aware:
                issued = self.issued_at.astimezone(UTC)
                expires = self.expires_at.astimezone(UTC)
            else:
                issued = self.issued_at
                expires = self.expires_at
            if expires < issued:
                raise ValueError("expires_at cannot be before issued_at")
        return self


class QualificationReviewRead(BaseModel):
    status: VerificationStatus
    reviewer_user_id: UUID
    reviewed_at: datetime
    review_notes: str | None


class QualificationRead(BaseModel):
    id: UUID
    coach_profile_id: UUID
    title: str
    issuing_organisation: str | None
    credential_reference: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    evidence_url: str | None
    verification_status: VerificationStatus
    reviews: list[QualificationReviewRead]
    created_at: datetime
    updated_at: datetime


class QualificationDecision(RequestModel):
    status: Literal[
        VerificationStatus.APPROVED,
        VerificationStatus.REJECTED,
        VerificationStatus.NEEDS_MORE_EVIDENCE,
    ]
    review_notes: str | None = Field(default=None, max_length=4000)


class QualificationDecisionRead(BaseModel):
    qualification_id: UUID
    status: VerificationStatus
    reviewer_user_id: UUID
    reviewed_at: datetime
    review_notes: str | None
