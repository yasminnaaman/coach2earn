"""Authentication and privileged account workflows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import AccountStatus, UserRole, VerificationStatus
from app.models.identity import CoachProfile, CoachVerification, User
from app.schemas.auth import normalize_email, validate_password_length
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
