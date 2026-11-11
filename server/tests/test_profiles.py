"""Profile ownership, discovery privacy, and qualification review API tests."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.commerce import CoachingPackage
from app.models.enums import UserRole, VerificationStatus
from app.models.identity import (
    CoachProfile,
    CoachQualification,
    CoachQualificationReview,
    CoachSpecialisation,
    Specialisation,
    User,
)
from app.seed_specialisations import seed_specialisations


def make_user(db_session, role: UserRole, email: str) -> User:
    user = User(
        email=email,
        password_hash="test-hash",
        role=role,
        date_of_birth=date(1995, 1, 1),
    )
    db_session.add(user)
    db_session.commit()
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def game_catalog_item(db_session) -> Specialisation:
    seed_specialisations(db_session)
    return db_session.scalar(
        select(Specialisation).where(Specialisation.slug == "rocket-league")
    )


def make_public_coach(db_session, spec: Specialisation, suffix: str = "one") -> tuple[User, CoachProfile]:
    user = User(
        email=f"coach-{suffix}@example.test",
        password_hash="test-hash",
        role=UserRole.COACH,
        coach_profile=CoachProfile(
            professional_bio="Rocket League rotations and mechanics coach",
            coaching_goals="Help players improve rotations and boost management",
            experience_years=6,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    db_session.add(user)
    db_session.flush()
    package = CoachingPackage(
        coach_profile=user.coach_profile,
        title="Five sessions",
        description="Private coaching package",
        price_amount=Decimal("100.00"),
        currency="USD",
        session_limit=5,
        duration_days=30,
        terms="Standard package terms",
    )
    db_session.add(package)
    db_session.commit()
    return user, user.coach_profile


def test_player_profile_create_read_update_and_protected_fields(api_client, db_session) -> None:
    user = make_user(db_session, UserRole.PLAYER, "player-profile@example.test")
    spec = game_catalog_item(db_session)
    headers = auth_headers(user)
    created = api_client.post(
        "/api/v1/profiles/player",
        headers=headers,
        json={
            "gaming_experience_years": 4,
            "skill_level": "diamond",
            "interests": ["mechanics"],
            "training_goals": "Improve rotations",
            "budget_amount": "25.00",
            "budget_currency": "USD",
            "game_ids": [str(spec.id)],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["gaming_experience_years"] == 4
    assert body["games"][0]["slug"] == "rocket-league"
    assert "user_id" not in body and "email" not in body

    read = api_client.get("/api/v1/profiles/player", headers=headers)
    assert read.status_code == 200
    assert read.json()["training_goals"] == "Improve rotations"
    assert api_client.get(f"/api/v1/profiles/player/{uuid4()}", headers=headers).status_code == 404

    updated = api_client.patch(
        "/api/v1/profiles/player",
        headers=headers,
        json={
            "skill_level": "champion",
            "budget_amount": "30.00",
            "budget_currency": "USD",
            "game_ids": [str(spec.id)],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["skill_level"] == "champion"
    assert updated.json()["budget_amount"] == "30.00"

    protected = api_client.patch(
        "/api/v1/profiles/player",
        headers=headers,
        json={"user_id": str(uuid4()), "role": "admin"},
    )
    assert protected.status_code == 422
    unpaired_currency = api_client.patch(
        "/api/v1/profiles/player",
        headers=headers,
        json={"budget_currency": None},
    )
    assert unpaired_currency.status_code == 422


def test_player_profile_rejects_invalid_catalog_and_role(api_client, db_session) -> None:
    player = make_user(db_session, UserRole.PLAYER, "player-invalid@example.test")
    another_player = make_user(db_session, UserRole.PLAYER, "player-other@example.test")
    coach = make_user(db_session, UserRole.COACH, "coach-role@example.test")
    invalid = api_client.post(
        "/api/v1/profiles/player",
        headers=auth_headers(player),
        json={"game_ids": [str(uuid4())]},
    )
    assert invalid.status_code == 422
    incomplete_budget = api_client.post(
        "/api/v1/profiles/player",
        headers=auth_headers(player),
        json={"budget_amount": "20.00"},
    )
    assert incomplete_budget.status_code == 422

    created = api_client.post(
        "/api/v1/profiles/player", headers=auth_headers(player), json={}
    )
    assert created.status_code == 201
    assert api_client.get("/api/v1/profiles/player", headers=auth_headers(another_player)).status_code == 404
    assert api_client.get("/api/v1/profiles/player", headers=auth_headers(coach)).status_code == 403


def test_coach_profile_crud_catalog_validation_and_protected_status(api_client, db_session) -> None:
    coach = make_user(db_session, UserRole.COACH, "coach-profile@example.test")
    spec = game_catalog_item(db_session)
    headers = auth_headers(coach)
    created = api_client.post(
        "/api/v1/profiles/coach",
        headers=headers,
        json={
            "professional_bio": "Competitive player and coach",
            "coaching_goals": "Teach rotations and boost management",
            "experience_years": 8,
            "specialisation_ids": [str(spec.id)],
        },
    )
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]
    assert created.json()["verification_status"] == "pending"

    invalid = api_client.patch(
        "/api/v1/profiles/coach",
        headers=headers,
        json={"specialisation_ids": [str(uuid4())]},
    )
    assert invalid.status_code == 422
    protected = api_client.patch(
        "/api/v1/profiles/coach",
        headers=headers,
        json={"verification_status": "approved", "user_id": str(uuid4())},
    )
    assert protected.status_code == 422

    updated = api_client.patch(
        "/api/v1/profiles/coach",
        headers=headers,
        json={
            "experience_years": 10,
            "coaching_goals": "Improve aerial control",
            "specialisation_ids": [str(spec.id)],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["experience_years"] == 10
    assert updated.json()["id"] == profile_id
    read = api_client.get("/api/v1/profiles/coach", headers=headers)
    assert read.status_code == 200
    assert read.json()["coaching_goals"] == "Improve aerial control"


def test_qualification_submission_is_private_and_admin_decisions_are_audited(
    api_client, db_session
) -> None:
    spec = game_catalog_item(db_session)
    coach, profile = make_public_coach(db_session, spec, "qualification")
    profile.verification_status = VerificationStatus.PENDING
    db_session.commit()
    admin = make_user(db_session, UserRole.ADMIN, "qualification-admin@example.test")
    coach_headers = auth_headers(coach)
    submitted = api_client.post(
        "/api/v1/profiles/coach/qualifications",
        headers=coach_headers,
        json={
            "title": "Regional coaching certificate",
            "issuing_organisation": "Example Federation",
            "credential_reference": "PRIVATE-REF-123",
            "evidence_url": "https://private.example.test/evidence/123",
        },
    )
    assert submitted.status_code == 201, submitted.text
    qualification_id = submitted.json()["id"]
    assert submitted.json()["verification_status"] == "pending"

    timezone_order = api_client.post(
        "/api/v1/profiles/coach/qualifications",
        headers=coach_headers,
        json={
            "title": "Timezone-aware dates",
            "issued_at": "2025-01-01T09:00:00+10:00",
            "expires_at": "2025-01-01T08:00:00+00:00",
        },
    )
    assert timezone_order.status_code == 201, timezone_order.text
    invalid_timezone_pair = api_client.post(
        "/api/v1/profiles/coach/qualifications",
        headers=coach_headers,
        json={
            "title": "Invalid timezone pair",
            "issued_at": "2025-01-01T09:00:00",
            "expires_at": "2025-01-01T10:00:00+00:00",
        },
    )
    assert invalid_timezone_pair.status_code == 422
    invalid_date_order = api_client.post(
        "/api/v1/profiles/coach/qualifications",
        headers=coach_headers,
        json={
            "title": "Expired before issue",
            "issued_at": "2025-01-02T10:00:00+00:00",
            "expires_at": "2025-01-01T10:00:00+00:00",
        },
    )
    assert invalid_date_order.status_code == 422

    own = api_client.get(
        "/api/v1/profiles/coach/qualifications", headers=coach_headers
    )
    assert own.status_code == 200
    private_submission = next(
        item for item in own.json() if item["id"] == qualification_id
    )
    assert private_submission["credential_reference"] == "PRIVATE-REF-123"
    other_coach = make_user(db_session, UserRole.COACH, "other-qualification-coach@example.test")
    other_profile = CoachProfile(user=other_coach, experience_years=1)
    db_session.add(other_profile)
    db_session.commit()
    other_qualifications = api_client.get(
        "/api/v1/profiles/coach/qualifications", headers=auth_headers(other_coach)
    )
    assert other_qualifications.status_code == 200
    assert other_qualifications.json() == []
    admin_queue = api_client.get(
        "/api/v1/admin/qualifications", headers=auth_headers(admin)
    )
    assert admin_queue.status_code == 200
    queued_item = next(item for item in admin_queue.json() if item["id"] == qualification_id)
    assert queued_item["coach_profile_id"] == str(profile.id)
    assert queued_item["credential_reference"] == "PRIVATE-REF-123"

    public = api_client.get(f"/api/v1/coaches/{profile.id}")
    assert public.status_code == 404  # Pending coaches are not publicly discoverable.
    profile.verification_status = VerificationStatus.APPROVED
    db_session.commit()
    public = api_client.get(f"/api/v1/coaches/{profile.id}")
    assert public.status_code == 200
    assert "PRIVATE-REF-123" not in public.text
    assert "evidence_url" not in public.text
    assert "private.example.test" not in public.text
    assert "user_id" not in public.json()

    assert api_client.get(
        "/api/v1/admin/qualifications", headers=coach_headers
    ).status_code == 403
    self_review = api_client.post(
        f"/api/v1/admin/qualifications/{qualification_id}/review",
        headers=coach_headers,
        json={"status": "approved"},
    )
    assert self_review.status_code == 403
    reviewed = api_client.post(
        f"/api/v1/admin/qualifications/{qualification_id}/review",
        headers=auth_headers(admin),
        json={"status": "approved", "review_notes": "Verified with issuer"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["reviewer_user_id"] == str(admin.id)
    assert reviewed.json()["reviewed_at"]
    qualification = db_session.get(CoachQualification, UUID(qualification_id))
    assert qualification.verification_status == VerificationStatus.APPROVED
    audit = db_session.scalar(
        select(CoachQualificationReview).where(
            CoachQualificationReview.qualification_id == qualification.id
        )
    )
    assert audit is not None
    assert audit.reviewer_user_id == admin.id
    assert audit.reviewed_at is not None

    repeated = api_client.post(
        f"/api/v1/admin/qualifications/{qualification_id}/review",
        headers=auth_headers(admin),
        json={"status": "rejected"},
    )
    assert repeated.status_code == 409

    second_submission = api_client.post(
        "/api/v1/profiles/coach/qualifications",
        headers=coach_headers,
        json={"title": "Advanced coaching credential"},
    )
    assert second_submission.status_code == 201
    rejected = api_client.post(
        f"/api/v1/admin/qualifications/{second_submission.json()['id']}/review",
        headers=auth_headers(admin),
        json={"status": "rejected", "review_notes": "Issuer could not confirm"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["reviewer_user_id"] == str(admin.id)


def test_coach_discovery_filters_currency_experience_goal_and_pagination(api_client, db_session) -> None:
    spec = game_catalog_item(db_session)
    _, first = make_public_coach(db_session, spec, "discovery-one")
    _, second = make_public_coach(db_session, spec, "discovery-two")
    second.experience_years = 2
    db_session.commit()

    base = api_client.get("/api/v1/coaches")
    assert base.status_code == 200, base.text
    assert len(base.json()) == 2
    assert api_client.get(
        "/api/v1/coaches", params={"specialisation_id": str(spec.id), "experience_years_min": 5}
    ).json()[0]["experience_years"] == 6

    by_goal = api_client.get("/api/v1/coaches", params={"goal": "boost management"})
    assert by_goal.status_code == 200
    assert len(by_goal.json()) == 2
    within_budget = api_client.get(
        "/api/v1/coaches",
        params={"budget_amount": "25", "budget_currency": "USD"},
    )
    assert within_budget.status_code == 200
    assert all(item["packages"][0]["price_per_session"] == "20.00" for item in within_budget.json())
    at_budget_boundary = api_client.get(
        "/api/v1/coaches",
        params={"budget_amount": "20.00", "budget_currency": "USD"},
    )
    assert len(at_budget_boundary.json()) == 2
    below_boundary = api_client.get(
        "/api/v1/coaches",
        params={"budget_amount": "19.99", "budget_currency": "USD"},
    )
    assert below_boundary.json() == []
    other_currency = api_client.get(
        "/api/v1/coaches",
        params={"budget_amount": "25", "budget_currency": "KES"},
    )
    assert other_currency.json() == []
    assert api_client.get(
        "/api/v1/coaches", params={"budget_amount": "25"}
    ).status_code == 422
    page = api_client.get("/api/v1/coaches", params={"offset": 1, "limit": 1})
    assert page.status_code == 200
    assert len(page.json()) == 1


def test_discovery_excludes_inactive_incomplete_and_unapproved_coaches(api_client, db_session) -> None:
    spec = game_catalog_item(db_session)
    make_public_coach(db_session, spec, "eligible")
    inactive = User(
        email="inactive-coach@example.test",
        password_hash="test-hash",
        role=UserRole.COACH,
        account_status="suspended",
        coach_profile=CoachProfile(
            professional_bio="Inactive coach",
            experience_years=5,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    incomplete = User(
        email="incomplete-coach@example.test",
        password_hash="test-hash",
        role=UserRole.COACH,
        coach_profile=CoachProfile(
            professional_bio=" ",
            experience_years=5,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    pending = User(
        email="pending-coach@example.test",
        password_hash="test-hash",
        role=UserRole.COACH,
        coach_profile=CoachProfile(
            professional_bio="Pending coach",
            experience_years=5,
            verification_status=VerificationStatus.PENDING,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    no_package = User(
        email="no-package-coach@example.test",
        password_hash="test-hash",
        role=UserRole.COACH,
        coach_profile=CoachProfile(
            professional_bio="Complete biography but no active package",
            experience_years=5,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    db_session.add_all([inactive, incomplete, pending, no_package])
    db_session.commit()
    response = api_client.get("/api/v1/coaches")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_discovery_rejects_invalid_filters_and_pagination(api_client) -> None:
    assert api_client.get("/api/v1/coaches", params={"offset": -1}).status_code == 422
    assert api_client.get("/api/v1/coaches", params={"limit": 101}).status_code == 422
    assert api_client.get("/api/v1/coaches", params={"goal": "   "}).status_code == 422
    assert api_client.get(
        "/api/v1/coaches", params={"budget_amount": "10", "budget_currency": "usd"}
    ).status_code == 422
    assert api_client.get(
        "/api/v1/coaches", params={"specialisation_id": str(uuid4())}
    ).status_code == 422
