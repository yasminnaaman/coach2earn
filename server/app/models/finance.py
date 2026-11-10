"""Coach earning accruals and separate payout records/allocations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import EarningStatus, PayoutStatus
from app.models.types import enum_column


class CoachEarning(TimestampMixin, Base):
    """An accrued earning; a payout never changes or duplicates this record."""

    __tablename__ = "coach_earnings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coaching_sessions.id", ondelete="RESTRICT"), unique=True
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[EarningStatus] = mapped_column(
        enum_column(EarningStatus, "earning_status"), nullable=False, default=EarningStatus.PENDING
    )

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="earnings")
    order: Mapped[Order] = relationship()
    session: Mapped[CoachingSession | None] = relationship(back_populates="earnings")
    allocations: Mapped[list[PayoutAllocation]] = relationship(
        back_populates="earning", overlaps="allocations,payout"
    )

    __table_args__ = (
        UniqueConstraint("id", "coach_profile_id", name="uq_earning_id_coach"),
        CheckConstraint("gross_amount >= 0", name="gross_nonnegative"),
        CheckConstraint("commission_amount >= 0", name="commission_nonnegative"),
        CheckConstraint("net_amount >= 0", name="net_nonnegative"),
        CheckConstraint("gross_amount = commission_amount + net_amount", name="amounts_reconcile"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        Index("ix_coach_earnings_coach_status", "coach_profile_id", "status"),
    )


class PayoutRecord(TimestampMixin, Base):
    """A payout record for integration reconciliation; it does not move funds."""

    __tablename__ = "payout_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(
        enum_column(PayoutStatus, "payout_status"), nullable=False, default=PayoutStatus.PENDING
    )
    external_reference: Mapped[str | None] = mapped_column(String(200), unique=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="payouts")
    allocations: Mapped[list[PayoutAllocation]] = relationship(
        back_populates="payout", passive_deletes="all", overlaps="allocations,earning"
    )

    __table_args__ = (
        UniqueConstraint("id", "coach_profile_id", name="uq_payout_id_coach"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        Index("ix_payout_records_coach_status", "coach_profile_id", "status"),
    )


class PayoutAllocation(Base):
    """Associates payout amounts to earnings without copying earnings as payouts."""

    __tablename__ = "payout_allocations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    payout_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    earning_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    payout: Mapped[PayoutRecord] = relationship(
        back_populates="allocations", overlaps="allocations,earning"
    )
    earning: Mapped[CoachEarning] = relationship(
        back_populates="allocations", overlaps="allocations,payout"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["payout_id", "coach_profile_id"],
            ["payout_records.id", "payout_records.coach_profile_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["earning_id", "coach_profile_id"],
            ["coach_earnings.id", "coach_earnings.coach_profile_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("payout_id", "earning_id", name="uq_payout_allocation_pair"),
        CheckConstraint("allocated_amount > 0", name="allocation_positive"),
        Index("ix_payout_allocations_earning_id", "earning_id"),
    )
