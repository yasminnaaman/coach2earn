"""Profile and qualification workflows with ownership checks at the API boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.commerce import CoachingPackage
from app.models.enums import AccountStatus, SpecialisationCategory, UserRole, VerificationStatus
from app.models.identity import (
    CoachProfile,
    CoachQualification,
    CoachQualificationReview,
    CoachSpecialisation,
    PlayerGame,
    PlayerProfile,
    Specialisation,
    User,
)
from app.schemas.profile import (
    CoachProfileCreate,
    CoachProfileRead,
    CoachProfileUpdate,
    PlayerProfileCreate,
    PlayerProfileRead,
    PlayerProfileUpdate,
    PublicCoachRead,
    PublicPackagePrice,
    QualificationCreate,
    QualificationDecision,
    QualificationDecisionRead,
    QualificationRead,
    QualificationReviewRead,
    SpecialisationRead,
)


class ProfileConflict(ValueError):
    """The requested profile operation conflicts with current state."""


class CatalogReferenceError(ValueError):
    """One or more requested catalog IDs do not identify game specialisations."""


class ProfileNotFound(LookupError):
    """A profile or qualification is not available to the current operation."""


def _game_specialisations(db: Session, ids: list[UUID]) -> list[Specialisation]:
    if not ids:
        return []
    rows = list(
        db.scalars(
            select(Specialisation).where(
                Specialisation.id.in_(ids),
                Specialisation.category == SpecialisationCategory.GAME,
            )
        )
    )
    if len(rows) != len(ids):
        raise CatalogReferenceError("One or more specialisation IDs are invalid")
    by_id = {row.id: row for row in rows}
    return [by_id[item_id] for item_id in ids]


def _specialisation_read(item: Specialisation) -> SpecialisationRead:
    return SpecialisationRead(
        id=item.id,
        category=item.category.value,
        name=item.name,
        slug=item.slug,
    )


def serialize_player_profile(profile: PlayerProfile) -> PlayerProfileRead:
    return PlayerProfileRead(
        id=profile.id,
        gaming_experience_years=profile.gaming_experience_years,
        skill_level=profile.skill_level,
        interests=profile.interests,
        training_goals=profile.training_goals,
        coaching_requirements=profile.coaching_requirements,
        budget_amount=profile.budget_amount,
        budget_currency=profile.budget_currency,
        games=[_specialisation_read(link.specialisation) for link in profile.games],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def serialize_coach_profile(profile: CoachProfile) -> CoachProfileRead:
    return CoachProfileRead(
        id=profile.id,
        professional_bio=profile.professional_bio,
        coaching_goals=profile.coaching_goals,
        experience_years=profile.experience_years,
        availability=profile.availability,
        verification_status=profile.verification_status,
        specialisations=[_specialisation_read(link.specialisation) for link in profile.specialisations],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def serialize_qualification(qualification: CoachQualification) -> QualificationRead:
    return QualificationRead(
        id=qualification.id,
        coach_profile_id=qualification.coach_profile_id,
        title=qualification.title,
        issuing_organisation=qualification.issuing_organisation,
        credential_reference=qualification.credential_reference,
        issued_at=qualification.issued_at,
        expires_at=qualification.expires_at,
        evidence_url=qualification.evidence_url,
        verification_status=qualification.verification_status,
        reviews=[
            QualificationReviewRead(
                status=review.status,
                reviewer_user_id=review.reviewer_user_id,
                reviewed_at=review.reviewed_at,
                review_notes=review.review_notes,
            )
            for review in qualification.reviews
        ],
        created_at=qualification.created_at,
        updated_at=qualification.updated_at,
    )


def create_player_profile(
    db: Session, user: User, payload: PlayerProfileCreate
) -> PlayerProfileRead:
    if user.role != UserRole.PLAYER:
        raise PermissionError("Only player accounts can create player profiles")
    if user.player_profile is not None:
        raise ProfileConflict("Player profile already exists")
    games = _game_specialisations(db, payload.game_ids)
    profile = PlayerProfile(
        user=user,
        gaming_experience_years=payload.gaming_experience_years,
        skill_level=payload.skill_level,
        interests=payload.interests,
        training_goals=payload.training_goals,
        coaching_requirements=payload.coaching_requirements,
        budget_amount=payload.budget_amount,
        budget_currency=payload.budget_currency,
        games=[PlayerGame(specialisation=item) for item in games],
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return serialize_player_profile(profile)


def update_player_profile(
    db: Session, user: User, payload: PlayerProfileUpdate
) -> PlayerProfileRead:
    profile = db.scalar(
        select(PlayerProfile)
        .options(selectinload(PlayerProfile.games).selectinload(PlayerGame.specialisation))
        .where(PlayerProfile.user_id == user.id)
    )
    if profile is None:
        raise ProfileNotFound("Player profile was not found")

    changes = payload.model_dump(exclude_unset=True)
    if "game_ids" in changes:
        ids = changes.pop("game_ids") or []
        games = _game_specialisations(db, ids)
        profile.games = [PlayerGame(specialisation=item) for item in games]
    if "budget_amount" in changes and changes["budget_amount"] is None:
        changes["budget_currency"] = None
    for field, value in changes.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(profile)
    return serialize_player_profile(profile)


def create_coach_profile(
    db: Session, user: User, payload: CoachProfileCreate
) -> CoachProfileRead:
    if user.role != UserRole.COACH:
        raise PermissionError("Only coach accounts can create coach profiles")
    if user.coach_profile is not None:
        raise ProfileConflict("Coach profile already exists")
    specialisations = _game_specialisations(db, payload.specialisation_ids)
    profile = CoachProfile(
        user=user,
        professional_bio=payload.professional_bio,
        coaching_goals=payload.coaching_goals,
        experience_years=payload.experience_years,
        availability=payload.availability,
        specialisations=[CoachSpecialisation(specialisation=item) for item in specialisations],
    )
    db.add(profile)
    db.commit()
    profile = get_coach_profile(db, user)
    assert profile is not None
    return serialize_coach_profile(profile)


def get_coach_profile(db: Session, user: User) -> CoachProfile | None:
    return db.scalar(
        select(CoachProfile)
        .options(
            selectinload(CoachProfile.specialisations).selectinload(CoachSpecialisation.specialisation)
        )
        .where(CoachProfile.user_id == user.id)
    )


def update_coach_profile(
    db: Session, user: User, payload: CoachProfileUpdate
) -> CoachProfileRead:
    profile = get_coach_profile(db, user)
    if profile is None:
        raise ProfileNotFound("Coach profile was not found")
    changes = payload.model_dump(exclude_unset=True)
    if "specialisation_ids" in changes:
        ids = changes.pop("specialisation_ids") or []
        specialisations = _game_specialisations(db, ids)
        profile.specialisations = [
            CoachSpecialisation(specialisation=item) for item in specialisations
        ]
    if "availability" in changes and changes["availability"] is None:
        changes.pop("availability")
    for field, value in changes.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(UTC)
    db.commit()
    profile = get_coach_profile(db, user)
    assert profile is not None
    return serialize_coach_profile(profile)


def create_qualification(
    db: Session, user: User, payload: QualificationCreate
) -> QualificationRead:
    profile = get_coach_profile(db, user)
    if profile is None:
        raise ProfileNotFound("Coach profile was not found")
    qualification = CoachQualification(
        coach_profile=profile,
        title=payload.title,
        issuing_organisation=payload.issuing_organisation,
        credential_reference=payload.credential_reference,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        evidence_url=str(payload.evidence_url) if payload.evidence_url else None,
        verification_status=VerificationStatus.PENDING,
    )
    db.add(qualification)
    db.commit()
    db.refresh(qualification)
    return serialize_qualification(qualification)


def list_qualifications(
    db: Session,
    *,
    coach_profile_id: UUID | None = None,
    status: VerificationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[CoachQualification]:
    statement = (
        select(CoachQualification)
        .options(selectinload(CoachQualification.reviews))
        .order_by(CoachQualification.created_at.desc(), CoachQualification.id)
        .offset(offset)
        .limit(limit)
    )
    if coach_profile_id is not None:
        statement = statement.where(CoachQualification.coach_profile_id == coach_profile_id)
    if status is not None:
        statement = statement.where(CoachQualification.verification_status == status)
    return list(db.scalars(statement))


def review_qualification(
    db: Session,
    qualification_id: UUID,
    reviewer: User,
    payload: QualificationDecision,
) -> QualificationDecisionRead:
    if reviewer.role != UserRole.ADMIN or reviewer.account_status != AccountStatus.ACTIVE:
        raise PermissionError("An active administrator must review qualifications")
    qualification = db.scalar(
        select(CoachQualification)
        .options(selectinload(CoachQualification.coach_profile))
        .where(CoachQualification.id == qualification_id)
        .with_for_update()
    )
    if qualification is None:
        raise ProfileNotFound("Qualification was not found")
    if qualification.coach_profile.user_id == reviewer.id:
        raise PermissionError("Coaches cannot review their own qualifications")
    if qualification.verification_status != VerificationStatus.PENDING:
        raise ProfileConflict("Only pending qualifications can be reviewed")
    reviewed_at = datetime.now(UTC)
    review = CoachQualificationReview(
        qualification=qualification,
        status=payload.status,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        review_notes=payload.review_notes,
    )
    qualification.verification_status = payload.status
    db.add(review)
    db.commit()
    return QualificationDecisionRead(
        qualification_id=qualification_id,
        status=payload.status,
        reviewer_user_id=reviewer.id,
        reviewed_at=reviewed_at,
        review_notes=payload.review_notes,
    )


def public_coach_statement(*, goal: str | None = None):
    statement = (
        select(CoachProfile)
        .join(CoachProfile.user)
        .where(
            User.role == UserRole.COACH,
            User.account_status == AccountStatus.ACTIVE,
            CoachProfile.verification_status == VerificationStatus.APPROVED,
            CoachProfile.professional_bio.is_not(None),
            func.length(func.trim(CoachProfile.professional_bio)) > 0,
            select(func.count(CoachSpecialisation.specialisation_id))
            .where(CoachSpecialisation.coach_profile_id == CoachProfile.id)
            .scalar_subquery()
            > 0,
            select(func.count(CoachingPackage.id))
            .where(
                CoachingPackage.coach_profile_id == CoachProfile.id,
                CoachingPackage.is_active.is_(True),
            )
            .scalar_subquery()
            > 0,
        )
    )
    if goal:
        escaped_goal = goal.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_goal}%"
        statement = statement.where(
            or_(
                CoachProfile.coaching_goals.ilike(pattern, escape="\\"),
                CoachProfile.professional_bio.ilike(pattern, escape="\\"),
            )
        )
    return statement


def display_name_from_email(email: str | None) -> str:
    """Readable placeholder name until users have a display-name field.

    "alex.mercer@x.io" -> "Alex Mercer". Only the local part is used; the
    full address is never exposed.
    """
    local = (email or "").split("@", 1)[0]
    words = [w for w in local.replace("_", ".").replace("-", ".").split(".") if w]
    return " ".join(w.capitalize() for w in words) or "Coach"


def coach_package_prices(
    db: Session, coach_profile_id: UUID, budget: Decimal | None = None, currency: str | None = None
) -> list[PublicPackagePrice]:
    statement = select(CoachingPackage).where(
        CoachingPackage.coach_profile_id == coach_profile_id,
        CoachingPackage.is_active.is_(True),
    )
    if budget is not None and currency is not None:
        statement = statement.where(
            CoachingPackage.currency == currency,
            CoachingPackage.price_amount <= budget * CoachingPackage.session_limit,
        )
    packages = list(db.scalars(statement.order_by(CoachingPackage.currency, CoachingPackage.price_amount)))
    return [
        PublicPackagePrice(
            title=package.title,
            price_per_session=(package.price_amount / package.session_limit).quantize(
                Decimal("0.01")
            ),
            currency=package.currency,
            session_limit=package.session_limit,
        )
        for package in packages
    ]


def serialize_public_coach(
    db: Session,
    profile: CoachProfile,
    *,
    budget: Decimal | None = None,
    currency: str | None = None,
) -> PublicCoachRead:
    profile = db.scalar(
        select(CoachProfile)
        .options(
            selectinload(CoachProfile.specialisations).selectinload(CoachSpecialisation.specialisation)
        )
        .where(CoachProfile.id == profile.id)
    )
    assert profile is not None
    return PublicCoachRead(
        id=profile.id,
        name=display_name_from_email(profile.user.email if profile.user else None),
        professional_bio=profile.professional_bio or "",
        coaching_goals=profile.coaching_goals,
        experience_years=profile.experience_years,
        specialisations=[
            _specialisation_read(link.specialisation) for link in profile.specialisations
        ],
        packages=coach_package_prices(db, profile.id, budget, currency),
    )
