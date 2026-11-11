"""Public registration/login and authenticated user profile endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    AuthenticationConfigurationError,
    CurrentUser,
    create_access_token,
    ensure_authentication_configured,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import AccountStatus, GuardianConsentStatus, UserRole
from app.models.identity import GuardianConsent, PlayerProfile, User
from app.schemas.auth import (
    AgeVerificationRequest,
    GuardianConsentResubmissionRequest,
    LoginRequest,
    PublicUser,
    RegisterRequest,
    TokenResponse,
    is_under_18,
    normalize_email,
)
from app.services.auth import AccountWorkflowError, resubmit_guardian_consent

router = APIRouter(prefix="/auth", tags=["authentication"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/register",
    response_model=PublicUser,
    status_code=status.HTTP_201_CREATED,
    summary="Register a player account",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """Create a player account; role fields are deliberately not accepted."""
    try:
        ensure_authentication_configured()
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    minor = is_under_18(payload.date_of_birth)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=UserRole.PLAYER,
        account_status=AccountStatus.ACTIVE,
        date_of_birth=payload.date_of_birth,
    )
    if minor:
        user.guardian_consent = GuardianConsent(
            guardian_name=payload.guardian_name,
            guardian_email=normalize_email(str(payload.guardian_email)),
            status=GuardianConsentStatus.PENDING,
            consent_version="guardian-consent-v1",
        )
    else:
        user.player_profile = PlayerProfile()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)
    return user


@router.post(
    "/age-verification",
    status_code=status.HTTP_200_OK,
    summary="Record age for a legacy account",
)
def verify_account_age(
    payload: AgeVerificationRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    """Backfill age for legacy accounts without exposing or changing it later."""
    if current_user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only player accounts can submit age verification")
    if current_user.date_of_birth is not None:
        raise HTTPException(status_code=409, detail="Date of birth has already been recorded")
    if payload.date_of_birth > date.today():
        raise HTTPException(status_code=422, detail="Date of birth cannot be in the future")
    minor = is_under_18(payload.date_of_birth)
    if minor and (not payload.guardian_name or not payload.guardian_email):
        raise HTTPException(status_code=422, detail="Guardian name and email are required for players under 18")
    if not minor and (payload.guardian_name is not None or payload.guardian_email is not None):
        raise HTTPException(status_code=422, detail="Guardian details are accepted only for players under 18")
    try:
        current_user.date_of_birth = payload.date_of_birth
        if minor:
            current_user.guardian_consent = GuardianConsent(
                guardian_name=payload.guardian_name,
                guardian_email=normalize_email(str(payload.guardian_email)),
                status=GuardianConsentStatus.PENDING,
                consent_version="guardian-consent-v1",
            )
        elif current_user.player_profile is None:
            current_user.player_profile = PlayerProfile()
        db.commit()
    except Exception:
        db.rollback()
        raise
    consent_status = current_user.guardian_consent_status
    return {"guardian_consent_status": consent_status.value if consent_status else None}


@router.put(
    "/guardian-consent",
    status_code=status.HTTP_200_OK,
    summary="Resubmit rejected guardian contact",
)
def update_guardian_consent(
    payload: GuardianConsentResubmissionRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if (
        current_user.role != UserRole.PLAYER
        or current_user.date_of_birth is None
        or not is_under_18(current_user.date_of_birth)
    ):
        raise HTTPException(status_code=403, detail="This account is not eligible to update guardian consent")
    try:
        consent = resubmit_guardian_consent(
            db, current_user, payload.guardian_name, normalize_email(str(payload.guardian_email))
        )
    except AccountWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"guardian_consent_status": consent.status.value}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a bearer access token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate without revealing whether an email is registered or active."""
    try:
        ensure_authentication_configured()
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    password_valid = verify_password(
        payload.password.get_secret_value(), user.password_hash if user is not None else None
    )
    if (
        user is None
        or not password_valid
        or user.account_status != AccountStatus.ACTIVE
    ):
        raise _invalid_credentials()

    settings = get_settings()
    try:
        access_token = create_access_token(user.id, settings)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get(
    "/me",
    response_model=PublicUser,
    summary="Get the authenticated user's public profile",
)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user
