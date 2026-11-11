"""Password hashing, JWT creation, and reusable authentication dependencies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from secrets import token_urlsafe
from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.enums import AccountStatus, GuardianConsentStatus, UserRole
from app.models.identity import User
from app.schemas.auth import is_under_18

JWT_ALGORITHM = "HS256"
_password_hash = PasswordHash.recommended()
_bearer_scheme = HTTPBearer(auto_error=False, scheme_name="JWTBearer")


class AuthenticationConfigurationError(RuntimeError):
    """Raised when authentication cannot operate with the current configuration."""


def _jwt_secret(settings: Settings) -> str:
    if settings.jwt_secret_key is None:
        raise AuthenticationConfigurationError("JWT_SECRET_KEY is not configured")
    return settings.jwt_secret_key.get_secret_value()


def ensure_authentication_configured(settings: Settings | None = None) -> None:
    """Fail closed instead of issuing tokens with a default or empty key."""
    _jwt_secret(settings or get_settings())


def hash_password(password: str) -> str:
    """Return an Argon2id hash; the caller must never log or return this value."""
    return _password_hash.hash(password)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Provide comparable password-hash work for unknown email addresses."""
    return _password_hash.hash(token_urlsafe(32))


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password without leaking malformed hashes or account existence."""
    candidate_hash = password_hash or _dummy_password_hash()
    try:
        verified = _password_hash.verify(password, candidate_hash)
    except UnknownHashError:
        verified = False
    if password_hash is None:
        return False
    return verified


def create_access_token(
    user_id: UUID,
    settings: Settings | None = None,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived signed token with no role or password data in its claims."""
    active_settings = settings or get_settings()
    now = datetime.now(UTC)
    lifetime = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=active_settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "iss": active_settings.jwt_issuer,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, _jwt_secret(active_settings), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> UUID:
    """Validate a signed, unexpired token and return its user subject."""
    active_settings = settings or get_settings()
    payload = jwt.decode(
        token,
        _jwt_secret(active_settings),
        algorithms=[JWT_ALGORITHM],
        issuer=active_settings.jwt_issuer,
        options={"require": ["sub", "iss", "iat", "exp"]},
    )
    return UUID(payload["sub"])


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db=Depends(get_db),
) -> User:
    """Resolve an active user from a token; role and status always come from the DB."""
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    except (InvalidTokenError, ValueError):
        raise _unauthorized() from None

    user = db.get(User, user_id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Build a reusable dependency restricting an endpoint to one or more roles."""
    permitted = frozenset(UserRole(role) for role in allowed_roles)

    def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if current_user.role == UserRole.PLAYER:
            if current_user.date_of_birth is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Date of birth must be recorded before player access is enabled",
                )
            if is_under_18(current_user.date_of_birth) and (
                current_user.guardian_consent is None
                or current_user.guardian_consent.status != GuardianConsentStatus.VERIFIED
                or current_user.player_profile is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Verified guardian consent is required for player access",
                )
        return current_user

    return role_dependency


require_player = require_roles(UserRole.PLAYER)
require_coach = require_roles(UserRole.COACH)
require_admin = require_roles(UserRole.ADMIN)
