"""Packages, quotation snapshots, orders, bookings and coaching sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import BookingStatus, OrderStatus, QuotationStatus, SessionStatus
from app.models.types import enum_column


def quotation_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=15)


class CoachingPackage(TimestampMixin, Base):
    __tablename__ = "coaching_packages"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    session_limit: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="packages")
    quotations: Mapped[list[Quotation]] = relationship(back_populates="package")

    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        CheckConstraint("session_limit > 0", name="session_limit_positive"),
        CheckConstraint("duration_days > 0", name="duration_positive"),
        Index("ix_coaching_packages_coach_active", "coach_profile_id", "is_active"),
    )


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    package_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coaching_packages.id", ondelete="SET NULL")
    )
    player_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("player_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    package_title: Mapped[str] = mapped_column(String(180), nullable=False)
    package_description: Mapped[str] = mapped_column(Text, nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    session_limit: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=quotation_expiry
    )
    status: Mapped[QuotationStatus] = mapped_column(
        enum_column(QuotationStatus, "quotation_status"), nullable=False, default=QuotationStatus.OPEN
    )

    package: Mapped[CoachingPackage | None] = relationship(back_populates="quotations")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="quotations")
    coach_profile: Mapped[CoachProfile] = relationship(back_populates="quotations")
    order: Mapped[Order | None] = relationship(back_populates="quotation", uselist=False)

    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        CheckConstraint("session_limit > 0", name="session_limit_positive"),
        CheckConstraint("duration_days > 0", name="duration_positive"),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        Index("ix_quotations_player_created", "player_profile_id", "created_at"),
        Index("ix_quotations_expiry_status", "expires_at", "status"),
    )


class Order(TimestampMixin, Base):
    """An order preserves the accepted quotation snapshot for its full lifetime."""

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    quotation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    package_title: Mapped[str] = mapped_column(String(180), nullable=False)
    package_description: Mapped[str] = mapped_column(Text, nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    session_limit: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        enum_column(OrderStatus, "order_status"), nullable=False, default=OrderStatus.PENDING_PAYMENT
    )

    quotation: Mapped[Quotation] = relationship(back_populates="order")
    booking: Mapped[Booking | None] = relationship(back_populates="order", uselist=False)

    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        CheckConstraint("session_limit > 0", name="session_limit_positive"),
        CheckConstraint("duration_days > 0", name="duration_positive"),
        Index("ix_orders_status_created", "status", "created_at"),
    )


class Booking(TimestampMixin, Base):
    """A purchased order has zero or one booking; a booking contains many sessions."""

    __tablename__ = "bookings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, "booking_status"), nullable=False, default=BookingStatus.PENDING
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped[Order] = relationship(back_populates="booking")
    sessions: Mapped[list[CoachingSession]] = relationship(
        back_populates="booking", order_by="CoachingSession.sequence_number", passive_deletes="all"
    )


class CoachingSession(TimestampMixin, Base):
    __tablename__ = "coaching_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        enum_column(SessionStatus, "session_status"), nullable=False, default=SessionStatus.SCHEDULED
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coach_notes: Mapped[str | None] = mapped_column(Text)

    booking: Mapped[Booking] = relationship(back_populates="sessions")
    points_transactions: Mapped[list[PointsTransaction]] = relationship(back_populates="session")
    earnings: Mapped[list[CoachEarning]] = relationship(back_populates="session")

    __table_args__ = (
        UniqueConstraint("booking_id", "sequence_number", name="uq_session_booking_sequence"),
        CheckConstraint("sequence_number > 0", name="sequence_positive"),
        CheckConstraint("ends_at > starts_at", name="end_after_start"),
        Index("ix_coaching_sessions_status_starts", "status", "starts_at"),
    )
