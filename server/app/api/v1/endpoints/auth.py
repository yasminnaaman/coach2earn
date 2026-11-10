"""Public registration/login and authenticated user profile endpoints."""

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
from app.models.enums import AccountStatus, UserRole
from app.models.identity import PlayerProfile, User
from app.schemas.auth import LoginRequest, PublicUser, RegisterRequest, TokenResponse

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
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=UserRole.PLAYER,
        account_status=AccountStatus.ACTIVE,
        player_profile=PlayerProfile(),
    )
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
