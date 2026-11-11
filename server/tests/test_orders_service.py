"""Database-level checks for order pricing, ownership and one-time acceptance."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.commerce import CoachingPackage
from app.models.enums import UserRole, VerificationStatus
from app.models.identity import CoachProfile, CoachSpecialisation, PlayerProfile, Specialisation, User
from app.seed_specialisations import seed_specialisations
from app.services.orders import CommerceError, accept_quotation, list_packages, player_quotation
from sqlalchemy import select


def test_server_pricing_snapshot_and_single_acceptance(db_session):
    seed_specialisations(db_session)
    game = db_session.scalar(select(Specialisation).where(Specialisation.slug == "rocket-league"))
    coach = User(email="svc-coach@test.local", password_hash="x", role=UserRole.COACH,
                 date_of_birth=date(1990, 1, 1), coach_profile=CoachProfile(
                     professional_bio="Coach bio", experience_years=2,
                     verification_status=VerificationStatus.APPROVED,
                     specialisations=[CoachSpecialisation(specialisation=game)]))
    player = User(email="svc-player@test.local", password_hash="x", role=UserRole.PLAYER,
                  date_of_birth=date(1990, 1, 1), player_profile=PlayerProfile())
    db_session.add_all([coach, player]); db_session.flush()
    package = CoachingPackage(coach_profile_id=coach.coach_profile.id, title="Package", description="Terms",
                              price_amount=Decimal("45.00"), currency="USD", session_limit=3,
                              duration_days=21, terms="No hidden fees")
    db_session.add(package); db_session.commit()

    assert [item.id for item in list_packages(db_session)] == [package.id]
    quotation = player_quotation(db_session, player, package.id)
    package.price_amount = Decimal("99.00")
    db_session.commit()
    order = accept_quotation(db_session, player, quotation.id)
    assert order.price_amount == Decimal("45.00")
    assert order.quotation.player_profile_id == player.player_profile.id
    assert order.quotation.coach_profile_id == coach.coach_profile.id
    assert order.order_reference.startswith("C2E-")
    with pytest.raises(CommerceError) as error:
        accept_quotation(db_session, player, quotation.id)
    assert error.value.status_code == 409


def test_quotation_cannot_be_accepted_by_another_player(db_session):
    player = User(email="owner@test.local", password_hash="x", role=UserRole.PLAYER,
                  date_of_birth=date(1990, 1, 1), player_profile=PlayerProfile())
    stranger = User(email="other@test.local", password_hash="x", role=UserRole.PLAYER,
                    date_of_birth=date(1990, 1, 1), player_profile=PlayerProfile())
    coach = User(email="owner-coach@test.local", password_hash="x", role=UserRole.COACH,
                 coach_profile=CoachProfile(professional_bio="Coach", experience_years=1))
    db_session.add_all([player, stranger, coach]); db_session.flush()
    from app.models.commerce import Quotation
    quote = Quotation(player_profile_id=player.player_profile.id, coach_profile_id=coach.coach_profile.id,
                      package_title="x", package_description="x", price_amount=Decimal("1"),
                      currency="USD", session_limit=1, duration_days=1, terms="")
    db_session.add(quote); db_session.commit()
    with pytest.raises(CommerceError) as error:
        accept_quotation(db_session, stranger, quote.id)
    assert error.value.status_code == 404
