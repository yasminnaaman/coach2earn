"""Player and coach profile management, public discovery, and qualification review."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import require_admin, require_coach, require_player
from app.db.session import get_db
from app.models.commerce import CoachingPackage
from app.models.enums import SpecialisationCategory, VerificationStatus
from app.models.identity import (
    CoachProfile,
    CoachSpecialisation,
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
    QualificationCreate,
    QualificationDecision,
    QualificationDecisionRead,
    QualificationRead,
)
from app.services.profiles import (
    CatalogReferenceError,
    ProfileConflict,
    ProfileNotFound,
    create_coach_profile,
    create_player_profile,
    create_qualification,
    get_coach_profile,
    list_qualifications,
    public_coach_statement,
    review_qualification,
    serialize_coach_profile,
    serialize_player_profile,
    serialize_public_coach,
    serialize_qualification,
    update_coach_profile,
    update_player_profile,
)

router = APIRouter()


def _translate_profile_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CatalogReferenceError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ProfileConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ProfileNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail="Profile operation could not be completed")


@router.post(
    "/profiles/player",
    response_model=PlayerProfileRead,
    status_code=status.HTTP_201_CREATED,
    tags=["player profiles"],
    summary="Create the authenticated player's profile",
)
def create_player(
    payload: PlayerProfileCreate,
    current_user: User = Depends(require_player),
    db: Session = Depends(get_db),
) -> PlayerProfileRead:
    try:
        return create_player_profile(db, current_user, payload)
    except (CatalogReferenceError, ProfileConflict, PermissionError) as exc:
        raise _translate_profile_error(exc) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Player profile already exists") from exc


@router.get(
    "/profiles/player",
    response_model=PlayerProfileRead,
    tags=["player profiles"],
    summary="Get the authenticated player's profile",
)
def read_player(
    current_user: User = Depends(require_player), db: Session = Depends(get_db)
) -> PlayerProfileRead:
    if current_user.player_profile is None:
        raise HTTPException(status_code=404, detail="Player profile was not found")
    profile = db.scalar(
        select(PlayerProfile).where(PlayerProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile was not found")
    return serialize_player_profile(profile)


@router.patch(
    "/profiles/player",
    response_model=PlayerProfileRead,
    tags=["player profiles"],
    summary="Update the authenticated player's profile",
)
def patch_player(
    payload: PlayerProfileUpdate,
    current_user: User = Depends(require_player),
    db: Session = Depends(get_db),
) -> PlayerProfileRead:
    try:
        return update_player_profile(db, current_user, payload)
    except (CatalogReferenceError, ProfileNotFound, PermissionError) as exc:
        raise _translate_profile_error(exc) from exc


@router.post(
    "/profiles/coach",
    response_model=CoachProfileRead,
    status_code=status.HTTP_201_CREATED,
    tags=["coach profiles"],
    summary="Create the authenticated coach's profile",
)
def create_coach(
    payload: CoachProfileCreate,
    current_user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> CoachProfileRead:
    try:
        return create_coach_profile(db, current_user, payload)
    except (CatalogReferenceError, ProfileConflict, PermissionError) as exc:
        raise _translate_profile_error(exc) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Coach profile already exists") from exc


@router.get(
    "/profiles/coach",
    response_model=CoachProfileRead,
    tags=["coach profiles"],
    summary="Get the authenticated coach's profile and verification status",
)
def read_coach(
    current_user: User = Depends(require_coach), db: Session = Depends(get_db)
) -> CoachProfileRead:
    profile = get_coach_profile(db, current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Coach profile was not found")
    return serialize_coach_profile(profile)


@router.patch(
    "/profiles/coach",
    response_model=CoachProfileRead,
    tags=["coach profiles"],
    summary="Update the authenticated coach's profile",
)
def patch_coach(
    payload: CoachProfileUpdate,
    current_user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> CoachProfileRead:
    try:
        return update_coach_profile(db, current_user, payload)
    except (CatalogReferenceError, ProfileNotFound, PermissionError) as exc:
        raise _translate_profile_error(exc) from exc


@router.post(
    "/profiles/coach/qualifications",
    response_model=QualificationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["coach qualifications"],
    summary="Submit qualification details and private evidence",
)
def submit_qualification(
    payload: QualificationCreate,
    current_user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> QualificationRead:
    try:
        return create_qualification(db, current_user, payload)
    except ProfileNotFound as exc:
        raise _translate_profile_error(exc) from exc


@router.get(
    "/profiles/coach/qualifications",
    response_model=list[QualificationRead],
    tags=["coach qualifications"],
    summary="List the authenticated coach's private qualifications",
)
def read_qualifications(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> list[QualificationRead]:
    profile = get_coach_profile(db, current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Coach profile was not found")
    return [
        serialize_qualification(qualification)
        for qualification in list_qualifications(
            db, coach_profile_id=profile.id, offset=offset, limit=limit
        )
    ]


@router.get(
    "/admin/qualifications",
    response_model=list[QualificationRead],
    tags=["qualification review"],
    summary="List submitted qualification evidence for review",
)
def review_queue(
    review_status: VerificationStatus = Query(default=VerificationStatus.PENDING, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[QualificationRead]:
    return [
        serialize_qualification(qualification)
        for qualification in list_qualifications(
            db, status=review_status, offset=offset, limit=limit
        )
    ]


@router.post(
    "/admin/qualifications/{qualification_id}/review",
    response_model=QualificationDecisionRead,
    tags=["qualification review"],
    summary="Approve or reject submitted qualification evidence",
)
def decide_qualification(
    qualification_id: UUID,
    payload: QualificationDecision,
    reviewer: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> QualificationDecisionRead:
    try:
        return review_qualification(db, qualification_id, reviewer, payload)
    except (ProfileConflict, ProfileNotFound, PermissionError) as exc:
        raise _translate_profile_error(exc) from exc


@router.get(
    "/coaches",
    response_model=list[PublicCoachRead],
    tags=["coach discovery"],
    summary="Discover publicly eligible coaches",
)
def discover_coaches(
    specialisation_id: UUID | None = None,
    experience_years_min: int | None = Query(default=None, ge=0, le=100),
    budget_amount: Decimal | None = Query(default=None, ge=0, max_digits=12, decimal_places=2),
    budget_currency: str | None = Query(default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"),
    goal: str | None = Query(default=None, min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PublicCoachRead]:
    if goal is not None:
        goal = goal.strip()
        if not goal:
            raise HTTPException(status_code=422, detail="goal cannot be blank")
    if (budget_amount is None) != (budget_currency is None):
        raise HTTPException(
            status_code=422, detail="budget_amount and budget_currency must be provided together"
        )
    statement = public_coach_statement(goal=goal)
    if experience_years_min is not None:
        statement = statement.where(CoachProfile.experience_years >= experience_years_min)
    if specialisation_id is not None:
        specialisation = db.get(Specialisation, specialisation_id)
        if specialisation is None or specialisation.category != SpecialisationCategory.GAME:
            raise HTTPException(status_code=422, detail="Invalid game specialisation ID")
        statement = statement.where(
            select(func.count(CoachSpecialisation.specialisation_id))
            .where(
                CoachSpecialisation.coach_profile_id == CoachProfile.id,
                CoachSpecialisation.specialisation_id == specialisation_id,
            )
            .scalar_subquery()
            > 0
        )
    if budget_amount is not None and budget_currency is not None:
        statement = statement.where(
            select(func.count(CoachingPackage.id))
            .where(
                CoachingPackage.coach_profile_id == CoachProfile.id,
                CoachingPackage.is_active.is_(True),
                CoachingPackage.currency == budget_currency,
                CoachingPackage.price_amount <= budget_amount * CoachingPackage.session_limit,
            )
            .scalar_subquery()
            > 0
        )
    profiles = list(
        db.scalars(statement.order_by(CoachProfile.created_at.desc(), CoachProfile.id).offset(offset).limit(limit))
    )
    return [
        serialize_public_coach(
            db, profile, budget=budget_amount, currency=budget_currency
        )
        for profile in profiles
    ]


@router.get(
    "/coaches/{coach_profile_id}",
    response_model=PublicCoachRead,
    tags=["coach discovery"],
    summary="Get an eligible public coach profile",
)
def public_coach(
    coach_profile_id: UUID, db: Session = Depends(get_db)
) -> PublicCoachRead:
    profile = db.scalar(
        public_coach_statement().where(CoachProfile.id == coach_profile_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Coach profile was not found")
    return serialize_public_coach(db, profile)


