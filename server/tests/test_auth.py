"""Authentication, JWT, account status, and role authorization tests."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import (
    AuthenticationConfigurationError,
    create_access_token,
    decode_access_token,
    hash_password,
    require_coach,
    verify_password,
)
from app.db.session import get_db
from app.models.enums import AccountStatus, UserRole, VerificationStatus
from app.models.identity import CoachProfile, CoachVerification, PlayerProfile, User

PASSWORD = "Correct Horse Battery 19!"


def test_register_creates_player_hash_and_safe_response(api_client, db_session, caplog) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "Hope.Example@example.com", "password": PASSWORD},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "hope.example@example.com"
    assert body["role"] == "player"
    assert body["account_status"] == "active"
    assert "password" not in body
    assert "password_hash" not in body
    assert PASSWORD not in response.text
    assert PASSWORD not in caplog.text

    user = db_session.scalar(select(User).where(User.email == body["email"]))
    assert user is not None
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)
    assert user.player_profile is not None


def test_duplicate_email_is_case_insensitive(api_client) -> None:
    first = api_client.post(
        "/api/v1/auth/register", json={"email": "person@example.com", "password": PASSWORD}
    )
    second = api_client.post(
        "/api/v1/auth/register", json={"email": "PERSON@example.com", "password": PASSWORD}
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "An account with this email already exists"}


def test_registration_rejects_role_elevation_and_redacts_invalid_password(api_client) -> None:
    elevated = api_client.post(
        "/api/v1/auth/register",
        json={"email": "attacker@example.com", "password": PASSWORD, "role": "admin"},
    )
    weak_password = "short"
    invalid = api_client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": weak_password},
    )

    assert elevated.status_code == 422
    assert weak_password not in elevated.text
    assert invalid.status_code == 422
    assert weak_password not in invalid.text


def test_password_hashing_and_verification() -> None:
    password_hash = hash_password(PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert verify_password(PASSWORD, password_hash)
    assert not verify_password("different password", password_hash)


def test_login_returns_bearer_token_and_me_returns_public_user(api_client) -> None:
    registration = api_client.post(
        "/api/v1/auth/register", json={"email": "login@example.com", "password": PASSWORD}
    )
    login = api_client.post(
        "/api/v1/auth/login", json={"email": "LOGIN@example.com", "password": PASSWORD}
    )

    assert registration.status_code == 201
    assert login.status_code == 200
    token_body = login.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["expires_in"] == get_settings().access_token_expire_minutes * 60
    assert PASSWORD not in login.text
    assert "password_hash" not in login.text

    me = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"
    assert "password_hash" not in me.json()
    assert PASSWORD not in me.text


def test_wrong_password_and_unknown_email_have_same_response(api_client) -> None:
    api_client.post(
        "/api/v1/auth/register", json={"email": "login-fail@example.com", "password": PASSWORD}
    )
    wrong_password = api_client.post(
        "/api/v1/auth/login",
        json={"email": "login-fail@example.com", "password": "Wrong Password 123!"},
    )
    unknown_email = api_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "Wrong Password 123!"},
    )

    assert wrong_password.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert "Wrong Password 123!" not in wrong_password.text


def test_invalid_and_expired_jwts_are_rejected(api_client, db_session) -> None:
    user = User(email="token@example.com", password_hash=hash_password(PASSWORD), role=UserRole.PLAYER)
    db_session.add(user)
    db_session.commit()
    expired_token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))

    invalid = api_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    expired = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert invalid.status_code == 401
    assert expired.status_code == 401
    assert invalid.headers["www-authenticate"] == "Bearer"


def test_inactive_accounts_cannot_login_or_use_existing_tokens(api_client, db_session) -> None:
    user = User(
        email="suspended@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.PLAYER,
        account_status=AccountStatus.SUSPENDED,
        player_profile=PlayerProfile(),
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)

    login = api_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    me = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 401
    assert me.status_code == 401


def test_missing_or_weak_jwt_secret_fails_closed() -> None:
    with pytest.raises(AuthenticationConfigurationError):
        create_access_token(uuid4(), Settings(jwt_secret_key=None))
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(jwt_secret_key="short")
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(jwt_secret_key="a" * 64)


def test_registration_is_unavailable_without_jwt_secret(api_client, monkeypatch) -> None:
    import app.core.security as security

    monkeypatch.setattr(security, "get_settings", lambda: Settings(jwt_secret_key=None))
    response = api_client.post(
        "/api/v1/auth/register", json={"email": "no-secret@example.com", "password": PASSWORD}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured"}


def test_role_dependency_protects_endpoint(api_client, db_engine, db_session) -> None:
    player = User(
        email="role-player@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.PLAYER,
        player_profile=PlayerProfile(),
    )
    db_session.add(player)
    db_session.commit()
    token = create_access_token(player.id)

    protected_app = FastAPI()

    @protected_app.get("/coach-only")
    def coach_only(user: User = Depends(require_coach)):
        return {"id": str(user.id), "role": user.role.value}

    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    protected_app.dependency_overrides[get_db] = override_db
    with TestClient(protected_app) as protected_client:
        response = protected_client.get(
            "/coach-only", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_admin_bootstrap_is_one_time_and_hashes_secret(db_session) -> None:
    from app.services.auth import AccountWorkflowError, bootstrap_admin

    admin = bootstrap_admin(db_session, "First.Admin@example.com", PASSWORD)

    assert admin.role == UserRole.ADMIN
    assert admin.password_hash != PASSWORD
    assert verify_password(PASSWORD, admin.password_hash)
    with pytest.raises(AccountWorkflowError, match="already been bootstrapped"):
        bootstrap_admin(db_session, "second.admin@example.com", PASSWORD)
    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() == 1


def test_admin_bootstrap_refuses_an_existing_email(db_session) -> None:
    from app.services.auth import AccountWorkflowError, bootstrap_admin

    db_session.add(
        User(email="existing@example.com", password_hash=hash_password(PASSWORD), role=UserRole.PLAYER)
    )
    db_session.commit()

    with pytest.raises(AccountWorkflowError, match="already uses that email"):
        bootstrap_admin(db_session, "EXISTING@example.com", PASSWORD)
    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() == 0


def test_cli_never_echoes_password_arguments(monkeypatch, capsys) -> None:
    import sys

    from app.cli import main

    command_line_password = "must-not-be-echoed"
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.cli", "bootstrap-admin", "--password", command_line_password],
    )

    assert main() == 2
    captured = capsys.readouterr()
    assert command_line_password not in captured.out
    assert command_line_password not in captured.err


def test_admin_coach_promotion_creates_profile_and_verification_atomically(
    api_client, db_session
) -> None:
    admin = User(email="reviewer@example.com", password_hash=hash_password(PASSWORD), role=UserRole.ADMIN)
    player = User(
        email="candidate@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.PLAYER,
        player_profile=PlayerProfile(),
    )
    db_session.add_all([admin, player])
    db_session.commit()
    admin_token = create_access_token(admin.id)

    response = api_client.post(
        f"/api/v1/admin/users/{player.id}/promote-to-coach",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"review_notes": "Qualifications reviewed"},
    )

    assert response.status_code == 201
    db_session.refresh(player)
    assert player.role == UserRole.COACH
    assert player.coach_profile is not None
    assert player.coach_profile.verification_status == VerificationStatus.APPROVED
    verification = db_session.scalar(
        select(CoachVerification).where(CoachVerification.coach_profile_id == player.coach_profile.id)
    )
    assert verification is not None
    assert verification.reviewer_user_id == admin.id


def test_non_admin_cannot_promote_coach(api_client, db_session) -> None:
    player = User(
        email="self-promote@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.PLAYER,
        player_profile=PlayerProfile(),
    )
    candidate = User(
        email="candidate-two@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.PLAYER,
        player_profile=PlayerProfile(),
    )
    db_session.add_all([player, candidate])
    db_session.commit()
    player_token = create_access_token(player.id)

    response = api_client.post(
        f"/api/v1/admin/users/{candidate.id}/promote-to-coach",
        headers={"Authorization": f"Bearer {player_token}"},
        json={},
    )

    assert response.status_code == 403
    db_session.refresh(candidate)
    assert candidate.role == UserRole.PLAYER
    assert candidate.coach_profile is None
