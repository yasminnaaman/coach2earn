"""Package and order API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PackageWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=10000)
    price_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    session_limit: int = Field(gt=0, le=32767)
    duration_days: int = Field(gt=0, le=32767)
    terms: str = Field(default="", max_length=10000)
    is_active: bool = True


class PackageRead(PackageWrite):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    coach_profile_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    package_id: UUID


class QuotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    package_id: UUID | None
    coach_profile_id: UUID
    package_title: str
    package_description: str
    price_amount: Decimal
    currency: str
    session_limit: int
    duration_days: int
    terms: str
    expires_at: datetime
    status: str
    created_at: datetime


class OrderAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quotation_id: UUID


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_reference: str
    quotation_id: UUID
    player_profile_id: UUID
    coach_profile_id: UUID
    package_title: str
    package_description: str
    price_amount: Decimal
    currency: str
    session_limit: int
    duration_days: int
    terms: str
    status: str
    created_at: datetime
    updated_at: datetime
