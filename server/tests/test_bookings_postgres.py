"""PostgreSQL-only booking constraints, locking, and concurrent booking protection."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import os
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.models.commerce import Booking, CoachAvailability, CoachingPackage, Order
from app.models.enums import BookingStatus, OrderStatus, SessionStatus, UserRole, VerificationStatus
from app.models.identity import CoachProfile, CoachSpecialisation, PlayerProfile, Specialisation, User
from app.seed_specialisations import seed_specialisations
from app.services.bookings import BookingError, create_booking
from app.schemas.bookings import BookingCreate

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to a migrated disposable PostgreSQL database",
)


def _setup(db):
    """Create a coach/player pair with a confirmed order."""
    seed_specialisations(db)
    spec = db.scalar(select(Specialisation).where(Specialisation.slug == "rocket-league"))
    coach = User(
        email=f"pg-coach-{uuid4().hex[:8]}@test.local",
        password_hash="x",
        role=UserRole.COACH,
        coach_profile=CoachProfile(
            professional_bio="PG Coach", experience_years=2,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    player = User(
        email=f"pg-player-{uuid4().hex[:8]}@test.local",
        password_hash="x",
        role=UserRole.PLAYER,
        player_profile=PlayerProfile(),
    )
    db.add_all([coach, player])
    db.flush()
    pkg = CoachingPackage(
        coach_profile_id=coach.coach_profile.id,
        title="PG Package", description="Desc",
        price_amount=Decimal("40.00"), currency="USD",
        session_limit=4, duration_days=28, terms="",
    )
    db.add(pkg)
    db.flush()

    from app.services.orders import player_quotation, accept_quotation
    quote = player_quotation(db, player, pkg.id)
    order = accept_quotation(db, player, quote.id)
    order.status = OrderStatus.CONFIRMED
    db.commit()
    db.refresh(order)
    return coach, player, order


def test_postgres_coach_availability_table_exists(db_session):
    result = db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'coach_availability'"
        )
    ).scalar()
    assert result == "coach_availability", "coach_availability table was not found in the database"


def test_postgres_availability_type_exclusive_constraint(db_session):
    """weekday and specific_date must be mutually exclusive."""
    from sqlalchemy.exc import IntegrityError

    coach_user = User(
        email=f"av-coach-{uuid4().hex[:8]}@test.local",
        password_hash="x",
        role=UserRole.COACH,
        coach_profile=CoachProfile(professional_bio="Test", experience_years=1),
    )
    db_session.add(coach_user)
    db_session.flush()

    av = CoachAvailability(
        coach_profile_id=coach_user.coach_profile.id,
        weekday=1,
        specific_date=datetime.now(UTC),  # Both set — violates constraint
        starts_at_utc="09:00",
        ends_at_utc="11:00",
        slot_duration_minutes=60,
    )
    db_session.add(av)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_postgres_concurrent_booking_creates_only_one(db_session):
    """Two simultaneous booking requests for the same slot must produce exactly one booking."""
    coach, player, order = _setup(db_session)
    session_factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    barrier = Barrier(2)
    starts_at = (datetime.now(UTC) + timedelta(days=7)).replace(
        hour=14, minute=0, second=0, microsecond=0, tzinfo=UTC
    )

    def attempt_booking():
        with session_factory() as session:
            current_player = session.get(User, player.id)
            barrier.wait(timeout=10)
            try:
                return create_booking(
                    session,
                    current_player,
                    BookingCreate(order_id=order.id, starts_at=starts_at),
                ).id
            except BookingError as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt_booking(), range(2)))

    # Exactly one booking must have been created
    from uuid import UUID
    successes = [r for r in outcomes if isinstance(r, UUID)]
    failures = [r for r in outcomes if r == 409]
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {outcomes}"
    assert len(failures) == 1
    assert db_session.scalar(select(Booking).where(Booking.order_id == order.id)) is not None
