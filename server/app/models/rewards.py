"""Append-only points ledger, redeemable rewards, prizes and coach bonuses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    BonusStatus,
    PointsSourceType,
    PointsTransactionType,
    PrizeStatus,
    RedemptionStatus,
)
from app.models.types import enum_column


class PointsTransaction(TimestampMixin, Base):
    """Immutable points ledger row; balances are the sum of signed deltas."""

    __tablename__ = "points_transactions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coaching_sessions.id", ondelete="RESTRICT"), unique=True
    )
    transaction_type: Mapped[PointsTransactionType] = mapped_column(
        enum_column(PointsTransactionType, "points_transaction_type"), nullable=False
    )
    source_type: Mapped[PointsSourceType] = mapped_column(
        enum_column(PointsSourceType, "points_source_type"), nullable=False
    )
    source_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    points_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="points_transactions")
    session: Mapped[CoachingSession | None] = relationship(back_populates="points_transactions")
    redemption: Mapped[RewardRedemption | None] = relationship(back_populates="points_transaction")

    __table_args__ = (
        UniqueConstraint("source_type", "source_reference", name="uq_points_source_reference"),
        CheckConstraint("points_delta <> 0", name="points_delta_nonzero"),
        CheckConstraint(
            "(transaction_type = 'earned' AND points_delta > 0) "
            "OR (transaction_type = 'redeemed' AND points_delta < 0) "
            "OR transaction_type = 'adjustment'",
            name="points_delta_matches_type",
        ),
        CheckConstraint("source_type <> 'session' OR session_id IS NOT NULL", name="session_source_has_session"),
        Index("ix_points_transactions_user_created", "user_id", "created_at"),
    )


def _reject_ledger_mutation(mapper: object, connection: object, target: PointsTransaction) -> None:
    raise ValueError("PointsTransaction is append-only; create a compensating ledger entry instead")


event.listen(PointsTransaction, "before_update", _reject_ledger_mutation)
event.listen(PointsTransaction, "before_delete", _reject_ledger_mutation)


class Reward(TimestampMixin, Base):
    __tablename__ = "rewards"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    redemptions: Mapped[list[RewardRedemption]] = relationship(back_populates="reward")

    __table_args__ = (CheckConstraint("points_cost > 0", name="points_cost_positive"),)


class RewardRedemption(TimestampMixin, Base):
    __tablename__ = "reward_redemptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reward_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rewards.id", ondelete="RESTRICT"), nullable=False
    )
    points_transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("points_transactions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    points_cost_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RedemptionStatus] = mapped_column(
        enum_column(RedemptionStatus, "redemption_status"), nullable=False, default=RedemptionStatus.PENDING
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
    reward: Mapped[Reward] = relationship(back_populates="redemptions")
    points_transaction: Mapped[PointsTransaction] = relationship(back_populates="redemption")

    __table_args__ = (
        CheckConstraint("points_cost_snapshot > 0", name="points_cost_positive"),
        Index("ix_reward_redemptions_user_created", "user_id", "created_at"),
    )


class Prize(TimestampMixin, Base):
    """A team prize pool that may create coach bonus obligations."""

    __tablename__ = "prizes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    prize_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PrizeStatus] = mapped_column(
        enum_column(PrizeStatus, "prize_status"), nullable=False, default=PrizeStatus.PENDING
    )

    team: Mapped[Team] = relationship(back_populates="prizes")
    bonuses: Mapped[list[Bonus]] = relationship(back_populates="prize")

    __table_args__ = (
        CheckConstraint("prize_amount >= 0", name="amount_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
        Index("ix_prizes_team_status", "team_id", "status"),
    )


class Bonus(TimestampMixin, Base):
    """A recorded coach share of a team prize, separate from payouts."""

    __tablename__ = "bonuses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    prize_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prizes.id", ondelete="RESTRICT"), nullable=False
    )
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[BonusStatus] = mapped_column(
        enum_column(BonusStatus, "bonus_status"), nullable=False, default=BonusStatus.PENDING
    )

    coach_profile: Mapped[CoachProfile] = relationship()
    prize: Mapped[Prize] = relationship(back_populates="bonuses")

    __table_args__ = (
        UniqueConstraint("coach_profile_id", "prize_id", name="uq_bonus_coach_prize"),
        CheckConstraint("percentage >= 0 AND percentage <= 100", name="percentage_range"),
        CheckConstraint("bonus_amount >= 0", name="amount_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_iso_length"),
    )
