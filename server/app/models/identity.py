"""Users, profiles, coach credentials, specialisations and teams."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    AccountStatus,
    SpecialisationCategory,
    TeamMemberRole,
    UserRole,
    VerificationStatus,
)
from app.models.types import enum_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "user_role"), nullable=False)
    account_status: Mapped[AccountStatus] = mapped_column(
        enum_column(AccountStatus, "account_status"), nullable=False, default=AccountStatus.ACTIVE
    )

    player_profile: Mapped[PlayerProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    coach_profile: Mapped[CoachProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    team_memberships: Mapped[list[TeamMembership]] = relationship(back_populates="user")
    points_transactions: Mapped[list[PointsTransaction]] = relationship(back_populates="user")

    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)


class PlayerProfile(TimestampMixin, Base):
    __tablename__ = "player_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    skill_level: Mapped[str | None] = mapped_column(String(80))
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    coaching_requirements: Mapped[str | None] = mapped_column(Text)
    training_goals: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="player_profile")
    quotations: Mapped[list[Quotation]] = relationship(back_populates="player_profile")


class CoachProfile(TimestampMixin, Base):
    __tablename__ = "coach_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    professional_bio: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    availability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        enum_column(VerificationStatus, "coach_verification_status"),
        nullable=False,
        default=VerificationStatus.PENDING,
    )

    user: Mapped[User] = relationship(back_populates="coach_profile")
    qualifications: Mapped[list[CoachQualification]] = relationship(
        back_populates="coach_profile", cascade="all, delete-orphan"
    )
    specialisations: Mapped[list[CoachSpecialisation]] = relationship(
        back_populates="coach_profile", cascade="all, delete-orphan"
    )
    verifications: Mapped[list[CoachVerification]] = relationship(
        back_populates="coach_profile", passive_deletes="all"
    )
    packages: Mapped[list[CoachingPackage]] = relationship(back_populates="coach_profile")
    quotations: Mapped[list[Quotation]] = relationship(back_populates="coach_profile")
    earnings: Mapped[list[CoachEarning]] = relationship(back_populates="coach_profile")
    payouts: Mapped[list[PayoutRecord]] = relationship(back_populates="coach_profile")

    __table_args__ = (CheckConstraint("experience_years >= 0", name="experience_nonnegative"),)


class CoachQualification(TimestampMixin, Base):
    __tablename__ = "coach_qualifications"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_organisation: Mapped[str | None] = mapped_column(String(200))
    credential_reference: Mapped[str | None] = mapped_column(String(200))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_url: Mapped[str | None] = mapped_column(String(2048))

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="qualifications")


class Specialisation(TimestampMixin, Base):
    __tablename__ = "specialisations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[SpecialisationCategory] = mapped_column(
        enum_column(SpecialisationCategory, "specialisation_category"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)

    coaches: Mapped[list[CoachSpecialisation]] = relationship(
        back_populates="specialisation", cascade="all, delete-orphan"
    )


class CoachSpecialisation(Base):
    __tablename__ = "coach_specialisations"

    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    specialisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specialisations.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="specialisations")
    specialisation: Mapped[Specialisation] = relationship(back_populates="coaches")


class CoachVerification(TimestampMixin, Base):
    __tablename__ = "coach_verifications"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[VerificationStatus] = mapped_column(
        enum_column(VerificationStatus, "verification_record_status"),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(2048))

    coach_profile: Mapped[CoachProfile] = relationship(back_populates="verifications")
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_user_id])


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[User] = relationship()
    memberships: Mapped[list[TeamMembership]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    prizes: Mapped[list[Prize]] = relationship(back_populates="team")


class TeamMembership(TimestampMixin, Base):
    __tablename__ = "team_memberships"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[TeamMemberRole] = mapped_column(
        enum_column(TeamMemberRole, "team_member_role"), nullable=False
    )

    team: Mapped[Team] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="team_memberships")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_membership_team_user"),
        Index("ix_team_memberships_user_id", "user_id"),
    )
