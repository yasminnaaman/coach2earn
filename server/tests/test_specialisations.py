"""Catalog seed, slug normalization and relationship integrity tests."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models.enums import SpecialisationCategory, UserRole
from app.models.identity import CoachProfile, CoachSpecialisation, Specialisation, User
from app.seed_specialisations import (
    INITIAL_SPECIALISATIONS,
    SpecialisationSeedConflict,
    seed_specialisations,
)


def test_specialisation_seed_is_repeatable_and_has_only_rocket_league(db_session) -> None:
    first_count = seed_specialisations(db_session)
    second_count = seed_specialisations(db_session)

    rows = list(db_session.scalars(select(Specialisation)))
    assert first_count == second_count == 1
    assert len(rows) == 1
    assert rows[0].category == SpecialisationCategory.GAME
    assert rows[0].name == "Rocket League"
    assert rows[0].slug == "rocket-league"
    assert len(INITIAL_SPECIALISATIONS) == 1


def test_seed_refuses_to_overwrite_conflicting_catalog_data(db_session) -> None:
    db_session.add(
        Specialisation(
            category=SpecialisationCategory.GAME,
            name="Different Game",
            slug="rocket-league",
        )
    )
    db_session.commit()

    with pytest.raises(SpecialisationSeedConflict, match="different data"):
        seed_specialisations(db_session)

    existing = db_session.scalar(
        select(Specialisation).where(Specialisation.slug == "rocket-league")
    )
    assert existing is not None and existing.name == "Different Game"


@pytest.mark.parametrize("slug", ["Rocket-League", "rocket_league", "-rocket", "rocket--league", "rocket-"])
def test_specialisation_rejects_noncanonical_slug(slug: str) -> None:
    with pytest.raises(ValueError, match="lowercase words separated by hyphens"):
        Specialisation(category=SpecialisationCategory.GAME, name="Rocket League", slug=slug)


def test_database_constraint_rejects_noncanonical_slug_bypassing_orm(db_session) -> None:
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO specialisations "
                "(id, category, name, slug) VALUES (:id, :category, :name, :slug)"
            ),
            {
                "id": str(uuid4()),
                "category": "game",
                "name": "Invalid slug",
                "slug": "invalid_slug",
            },
        )
    db_session.rollback()


def test_specialisation_slug_is_unique(db_session) -> None:
    db_session.add_all(
        [
            Specialisation(category=SpecialisationCategory.GAME, name="Rocket League", slug="rocket-league"),
            Specialisation(category=SpecialisationCategory.GAME, name="Another Name", slug="rocket-league"),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_coach_specialisation_rejects_invalid_foreign_key(db_session) -> None:
    user = User(email="catalog-coach@example.test", password_hash="hash", role=UserRole.COACH)
    profile = CoachProfile(user=user)
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        CoachSpecialisation(coach_profile_id=profile.id, specialisation_id=uuid4())
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_referenced_specialisation_cannot_be_deleted(db_session) -> None:
    user = User(email="referenced-coach@example.test", password_hash="hash", role=UserRole.COACH)
    profile = CoachProfile(user=user)
    specialisation = Specialisation(
        category=SpecialisationCategory.GAME, name="Rocket League", slug="rocket-league"
    )
    link = CoachSpecialisation(coach_profile=profile, specialisation=specialisation)
    db_session.add_all([user, profile, specialisation, link])
    db_session.commit()

    db_session.delete(specialisation)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
    assert db_session.scalar(
        select(func.count()).select_from(CoachSpecialisation)
    ) == 1


@pytest.mark.parametrize(
    "transaction_values",
    [
        {"transaction_type": "earned", "points_delta": 0, "source_type": "admin_action", "source_reference": "zero"},
        {"transaction_type": "earned", "points_delta": -1, "source_type": "admin_action", "source_reference": "negative-earned"},
        {"transaction_type": "redeemed", "points_delta": 1, "source_type": "redemption", "source_reference": "positive-redeem"},
        {"transaction_type": "earned", "points_delta": 1, "source_type": "session", "source_reference": "missing-session"},
    ],
)
def test_points_ledger_rejects_invalid_rows(db_session, transaction_values) -> None:
    user = User(email=f"ledger-{uuid4().hex}@example.test", password_hash="hash", role=UserRole.PLAYER)
    db_session.add(user)
    db_session.flush()
    values = {
        "id": str(uuid4()),
        "user_id": str(user.id),
        "session_id": None,
        "transaction_type": transaction_values["transaction_type"],
        "source_type": transaction_values["source_type"],
        "source_reference": transaction_values["source_reference"],
        "points_delta": transaction_values["points_delta"],
    }
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO points_transactions "
                "(id, user_id, session_id, transaction_type, source_type, source_reference, points_delta) "
                "VALUES (:id, :user_id, :session_id, :transaction_type, :source_type, :source_reference, :points_delta)"
            ),
            values,
        )
    db_session.rollback()
