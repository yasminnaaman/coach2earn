"""Authentication and privileged account workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import (
    AccountStatus,
    GuardianConsentStatus,
    UserRole,
    VerificationStatus,
)
from app.models.identity import (
    CoachProfile,
    CoachVerification,
    GuardianConsent,
    GuardianConsentDecision,
    PlayerProfile,
    User,
)
from app.schemas.auth import is_under_18, normalize_email, validate_password_length
from pydantic import SecretStr

ADMIN_BOOTSTRAP_LOCK_ID = 0x434F41434832


class AccountWorkflowError(ValueError):
    """Raised when an administrative account workflow cannot be completed."""


def bootstrap_admin(db: Session, email: str, password: str) -> User:
    """Create exactly one initial admin under a transaction-level PostgreSQL lock."""
    try:
        validate_password_length(SecretStr(password))
    except ValueError as exc:
        raise AccountWorkflowError(str(exc)) from None
    normalized_email = normalize_email(email)
    try:
        with db.begin():
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": ADMIN_BOOTSTRAP_LOCK_ID},
                )
            has_admin = db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1))
            if has_admin is not None:
                raise AccountWorkflowError("An administrator account has already been bootstrapped")
            existing_user = db.scalar(
                select(User.id).where(func.lower(User.email) == normalized_email).limit(1)
            )
            if existing_user is not None:
                raise AccountWorkflowError("An account already uses that email address")

            user = User(
                email=normalized_email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                account_status=AccountStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
            return user
    except IntegrityError as exc:
        db.rollback()
        raise AccountWorkflowError("Bootstrap could not create the administrator account") from exc


def promote_user_to_coach(
    db: Session,
    user_id: UUID,
    reviewer: User,
    review_notes: str | None = None,
) -> User:
    """Promote an active player and create approved coach records atomically."""
    try:
        target = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if target is None:
            raise AccountWorkflowError("User was not found")
        if reviewer.role != UserRole.ADMIN or reviewer.account_status != AccountStatus.ACTIVE:
            raise AccountWorkflowError("An active administrator must approve coach promotion")
        if target.account_status != AccountStatus.ACTIVE:
            raise AccountWorkflowError("Inactive accounts cannot be promoted")
        if target.date_of_birth is None:
            raise AccountWorkflowError("Date of birth must be recorded before coach promotion")
        if is_under_18(target.date_of_birth) and (
            target.guardian_consent is None
            or target.guardian_consent.status != GuardianConsentStatus.VERIFIED
        ):
            raise AccountWorkflowError("Verified guardian consent is required before coach promotion")
        if target.role != UserRole.PLAYER or target.coach_profile is not None:
            raise AccountWorkflowError("Only a player without a coach profile can be promoted")

        coach_profile = CoachProfile(
            user=target,
            verification_status=VerificationStatus.APPROVED,
        )
        verification = CoachVerification(
            coach_profile=coach_profile,
            reviewer=reviewer,
            status=VerificationStatus.APPROVED,
            reviewed_at=datetime.now(UTC),
            review_notes=review_notes,
        )
        target.role = UserRole.COACH
        db.add_all([coach_profile, verification])
        db.commit()
        db.refresh(target)
        return target
    except Exception:
        db.rollback()
        raise


def review_coach_verification(
    db: Session,
    user_id: UUID,
    reviewer: User,
    status: VerificationStatus,
    review_notes: str | None = None,
) -> CoachVerification:
    """Record an administrator decision for a coach, preserving each review."""
    if reviewer.role != UserRole.ADMIN or reviewer.account_status != AccountStatus.ACTIVE:
        raise AccountWorkflowError("An active administrator must review coach verification")
    if reviewer.id == user_id:
        raise AccountWorkflowError("Administrators cannot review their own coach profile")
    target = db.get(User, user_id)
    if target is None or target.role != UserRole.COACH or target.coach_profile is None:
        raise AccountWorkflowError("Coach profile was not found")
    if target.account_status != AccountStatus.ACTIVE:
        raise AccountWorkflowError("Inactive accounts cannot be reviewed")
    if status not in {
        VerificationStatus.APPROVED,
        VerificationStatus.REJECTED,
        VerificationStatus.NEEDS_MORE_EVIDENCE,
    }:
        raise AccountWorkflowError("Invalid coach verification decision")

    try:
        with db.begin_nested():
            target.coach_profile.verification_status = status
            verification = CoachVerification(
                coach_profile=target.coach_profile,
                status=status,
                reviewer=reviewer,
                reviewed_at=datetime.now(UTC),
                review_notes=review_notes,
            )
            db.add(verification)
            db.flush()
        db.commit()
        return verification
    except Exception:
        db.rollback()
        raise


def review_guardian_consent(
    db: Session,
    user_id: UUID,
    reviewer: User,
    status: GuardianConsentStatus,
    evidence_reference: str,
    review_notes: str | None = None,
) -> GuardianConsent:
    """Review consent and create the player profile only after verification."""
    if reviewer.role != UserRole.ADMIN or reviewer.account_status != AccountStatus.ACTIVE:
        raise AccountWorkflowError("An active administrator must review guardian consent")
    try:
        with db.begin_nested():
            target = db.scalar(select(User).where(User.id == user_id).with_for_update())
            if target is None or target.role != UserRole.PLAYER:
                raise AccountWorkflowError("Player account was not found")
            if target.date_of_birth is None or not is_under_18(target.date_of_birth):
                raise AccountWorkflowError("Guardian consent is only valid for under-18 accounts")
            consent = target.guardian_consent
            if consent is None:
                raise AccountWorkflowError("Guardian consent was not found")
            if consent.status == GuardianConsentStatus.VERIFIED:
                raise AccountWorkflowError("Guardian consent is already verified")
            if reviewer.id == target.id:
                raise AccountWorkflowError("Players cannot verify their own guardian consent")
            consent.status = status
            db.add(
                GuardianConsentDecision(
                    consent=consent,
                    status=status,
                    reviewer=reviewer,
                    reviewed_at=datetime.now(UTC),
                    evidence_reference=evidence_reference,
                    review_notes=review_notes,
                )
            )
            if status == GuardianConsentStatus.VERIFIED and target.player_profile is None:
                target.player_profile = PlayerProfile()
            db.flush()
        db.commit()
        db.refresh(consent)
        return consent
    except Exception:
        db.rollback()
        raise


def resubmit_guardian_consent(
    db: Session, user: User, guardian_name: str, guardian_email: str
) -> GuardianConsent:
    """Allow the account owner to correct guardian contact after rejection."""
    consent = user.guardian_consent
    if consent is None or consent.status != GuardianConsentStatus.REJECTED:
        raise AccountWorkflowError("Only rejected guardian consent can be resubmitted")
    consent.guardian_name = guardian_name
    consent.guardian_email = normalize_email(guardian_email)
    consent.status = GuardianConsentStatus.PENDING
    db.commit()
    db.refresh(consent)
    return consent
