"""Availability and booking API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AvailabilityWrite(BaseModel):
    """Create or update a coach availability window."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    weekday: int | None = Field(
        default=None,
        description="ISO weekday 1=Mon … 7=Sun. Mutually exclusive with specific_date.",
        ge=1,
        le=7,
    )
    specific_date: datetime | None = Field(
        default=None,
        description="UTC datetime for a one-off availability block.",
    )
    starts_at_utc: str = Field(
        pattern=r"^\d{2}:\d{2}$",
        description="HH:MM start of the window in UTC.",
    )
    ends_at_utc: str = Field(
        pattern=r"^\d{2}:\d{2}$",
        description="HH:MM end of the window in UTC.",
    )
    slot_duration_minutes: int = Field(gt=0, le=480)
    is_active: bool = True

    @model_validator(mode="after")
    def check_type_exclusive(self) -> AvailabilityWrite:
        if (self.weekday is None) == (self.specific_date is None):
            raise ValueError("Exactly one of weekday or specific_date must be provided")
        if self.starts_at_utc >= self.ends_at_utc:
            raise ValueError("starts_at_utc must be before ends_at_utc")
        return self


class AvailabilityRead(AvailabilityWrite):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    coach_profile_id: UUID
    created_at: datetime
    updated_at: datetime


class AvailableSlot(BaseModel):
    """A single bookable time slot derived from availability rules."""

    starts_at: datetime
    ends_at: datetime
    availability_id: UUID


class BookingCreate(BaseModel):
    """Request body when a player creates a booking."""

    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    starts_at: datetime = Field(description="Requested session start time (UTC).")
    notes: str | None = Field(default=None, max_length=2000)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    sequence_number: int
    starts_at: datetime
    ends_at: datetime
    status: str
    confirmed_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    coach_notes: str | None
    created_at: datetime
    updated_at: datetime


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: str
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    sessions: list[SessionRead]
    created_at: datetime
    updated_at: datetime


class BookingStatusUpdate(BaseModel):
    """Transition a booking to a new status."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["confirmed", "cancelled", "completed"]
    notes: str | None = Field(default=None, max_length=2000)


class SessionStatusUpdate(BaseModel):
    """Transition a single coaching session status."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["confirmed", "completed", "cancelled"]
    coach_notes: str | None = Field(default=None, max_length=4000)
