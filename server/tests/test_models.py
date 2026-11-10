"""Model relationship, snapshot, and integrity tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.commerce import Booking, CoachingPackage, CoachingSession, Order, Quotation
from app.models.enums import (
    BookingStatus,
    OrderStatus,
    PointsSourceType,
    PointsTransactionType,
    SessionStatus,
    UserRole,
)
from app.models.enums import SpecialisationCategory, VerificationStatus
from app.models.identity import (
    CoachProfile,
    CoachQualification,
    CoachSpecialisation,
    CoachVerification,
    PlayerProfile,
    Specialisation,
    Team,
    TeamMembership,
    User,
)
from app.models.finance import CoachEarning, PayoutAllocation, PayoutRecord
from app.models.rewards import (
    Bonus,
    PointsTransaction,
    Prize,
    Reward,
    RewardRedemption,
)


def make_order_graph(db_session):
    player = User(email="player@example.test", password_hash="test-hash", role=UserRole.PLAYER)
    coach_user = User(email="coach@example.test", password_hash="test-hash", role=UserRole.COACH)
    player_profile = PlayerProfile(user=player, skill_level="intermediate")
    coach_profile = CoachProfile(user=coach_user, experience_years=4)
    package = CoachingPackage(
        coach_profile=coach_profile,
        title="Five sessions",
        description="Rocket League coaching",
        price_amount=Decimal("125.00"),
        currency="USD",
        session_limit=5,
        duration_days=30,
        terms="Sessions expire after 30 days.",
    )
    quote = Quotation(
        package=package,
        player_profile=player_profile,
        coach_profile=coach_profile,
        package_title=package.title,
        package_description=package.description,
        price_amount=package.price_amount,
        currency=package.currency,
        session_limit=package.session_limit,
        duration_days=package.duration_days,
        terms=package.terms,
    )
    order = Order(
        quotation=quote,
        package_title=quote.package_title,
        package_description=quote.package_description,
        price_amount=quote.price_amount,
        currency=quote.currency,
        session_limit=quote.session_limit,
        duration_days=quote.duration_days,
        terms=quote.terms,
        status=OrderStatus.PENDING_PAYMENT,
    )
    booking = Booking(order=order, status=BookingStatus.PENDING)
    session = CoachingSession(
        booking=booking,
        sequence_number=1,
        starts_at=datetime.now(UTC) + timedelta(days=1),
        ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        status=SessionStatus.SCHEDULED,
    )
    db_session.add_all([player, coach_user, package, quote, order, booking, session])
    db_session.flush()
    return player, player_profile, coach_profile, package, quote, order, booking, session


def test_models_create_and_relationship_cardinality(db_session) -> None:
    _, player, coach, _, quote, order, booking, session = make_order_graph(db_session)
    db_session.commit()

    assert quote.player_profile is player
    assert quote.coach_profile is coach
    assert quote.order is order
    assert order.booking is booking
    assert booking.order is order
    assert booking.sessions == [session]
    assert session.booking is booking


def test_quotation_and_order_keep_package_snapshots(db_session) -> None:
    _, _, _, package, quote, order, _, _ = make_order_graph(db_session)
    db_session.commit()

    package.title = "Updated package"
    package.price_amount = Decimal("200.00")
    package.terms = "New terms apply to future quotations only."
    db_session.commit()
    db_session.expire_all()

    assert quote.package.title == "Updated package"
    assert quote.package_title == "Five sessions"
    assert quote.price_amount == Decimal("125.00")
    assert quote.terms == "Sessions expire after 30 days."
    assert order.package_title == "Five sessions"
    assert order.price_amount == Decimal("125.00")
    assert order.terms == "Sessions expire after 30 days."


def test_quotation_expiry_defaults_to_fifteen_minutes(db_session) -> None:
    *_, quote, _, _, _ = make_order_graph(db_session)
    db_session.commit()

    expiry = quote.expires_at
    created_at = quote.created_at
    if expiry.tzinfo is None:  # SQLite does not preserve timezone metadata.
        expiry = expiry.replace(tzinfo=UTC)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    assert timedelta(minutes=14, seconds=58) <= expiry - created_at <= timedelta(minutes=15, seconds=2)


def test_case_insensitive_email_uniqueness(db_session) -> None:
    player, _, _, _, _, _, _, _ = make_order_graph(db_session)
    duplicate_email = User(
        email="PLAYER@example.test", password_hash="test-hash", role=UserRole.PLAYER
    )
    db_session.add(duplicate_email)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_team_membership_is_unique_per_team_and_user(db_session) -> None:
    player, _, _, _, _, _, _, _ = make_order_graph(db_session)
    team = Team(created_by=player, name="Test team")
    db_session.add(team)
    db_session.flush()
    db_session.add(TeamMembership(team=team, user=player, role="owner"))
    db_session.flush()
    db_session.add(TeamMembership(team=team, user=player, role="player"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_financial_reward_and_coach_records_link_correctly(db_session) -> None:
    player, _, coach, _, _, order, _, session = make_order_graph(db_session)
    admin = User(email="admin@example.test", password_hash="test-hash", role=UserRole.ADMIN)
    team = Team(created_by=admin, name="Prize team")
    qualification = CoachQualification(coach_profile=coach, title="Advanced coaching")
    specialisation = Specialisation(
        category=SpecialisationCategory.GAME, name="Rocket League", slug="rocket-league"
    )
    coach_specialisation = CoachSpecialisation(
        coach_profile=coach, specialisation=specialisation
    )
    verification = CoachVerification(
        coach_profile=coach,
        reviewer=admin,
        status=VerificationStatus.APPROVED,
    )
    prize = Prize(team=team, name="Regional tournament", prize_amount=Decimal("1000.00"), currency="USD")
    bonus = Bonus(
        coach_profile=coach,
        prize=prize,
        percentage=Decimal("7.00"),
        bonus_amount=Decimal("70.00"),
        currency="USD",
    )
    points = PointsTransaction(
        user=player,
        session=session,
        transaction_type=PointsTransactionType.EARNED,
        source_type=PointsSourceType.SESSION,
        source_reference=str(session.id),
        points_delta=10,
    )
    reward = Reward(name="Training guide", description="Digital guide", points_cost=10)
    redemption_points = PointsTransaction(
        user=player,
        transaction_type=PointsTransactionType.REDEEMED,
        source_type=PointsSourceType.REDEMPTION,
        source_reference="redemption-record-1",
        points_delta=-10,
    )
    redemption = RewardRedemption(
        user=player,
        reward=reward,
        points_transaction=redemption_points,
        points_cost_snapshot=10,
    )
    earning = CoachEarning(
        coach_profile=coach,
        order=order,
        session=session,
        gross_amount=Decimal("100.00"),
        commission_amount=Decimal("8.00"),
        net_amount=Decimal("92.00"),
        currency="USD",
    )
    payout = PayoutRecord(coach_profile=coach, amount=Decimal("92.00"), currency="USD")
    allocation = PayoutAllocation(
        coach_profile_id=coach.id,
        payout=payout,
        earning=earning,
        allocated_amount=Decimal("92.00"),
    )
    db_session.add_all(
        [
            admin,
            team,
            qualification,
            specialisation,
            coach_specialisation,
            verification,
            prize,
            bonus,
            points,
            reward,
            redemption,
            earning,
            payout,
            allocation,
        ]
    )
    db_session.commit()

    assert coach.qualifications == [qualification]
    assert coach.specialisations == [coach_specialisation]
    assert coach.verifications == [verification]
    assert prize.bonuses == [bonus]
    assert redemption.points_transaction is redemption_points
    assert payout.allocations == [allocation]
    assert earning.allocations == [allocation]


def test_points_ledger_source_is_unique_and_append_only(db_session) -> None:
    user = User(email="ledger@example.test", password_hash="test-hash", role=UserRole.PLAYER)
    transaction = PointsTransaction(
        user=user,
        transaction_type=PointsTransactionType.EARNED,
        source_type=PointsSourceType.ADMIN_ACTION,
        source_reference="admin-action-123",
        points_delta=25,
    )
    db_session.add(transaction)
    db_session.commit()
    transaction_id = transaction.id

    transaction.points_delta = 50
    with pytest.raises(ValueError, match="append-only"):
        db_session.flush()
    db_session.rollback()

    persisted_transaction = db_session.get(PointsTransaction, transaction_id)
    db_session.delete(persisted_transaction)
    with pytest.raises(ValueError, match="append-only"):
        db_session.flush()
    db_session.rollback()

    duplicate = PointsTransaction(
        user=user,
        transaction_type=PointsTransactionType.EARNED,
        source_type=PointsSourceType.ADMIN_ACTION,
        source_reference="admin-action-123",
        points_delta=25,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
