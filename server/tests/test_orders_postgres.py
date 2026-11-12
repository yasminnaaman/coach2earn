"""PostgreSQL-only order constraints, locking, and migration assumptions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import os
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.commerce import CoachingPackage, Order
from app.models.enums import UserRole
from app.models.identity import User
from app.services.orders import CommerceError, accept_quotation, player_quotation
from test_orders import setup_pair


pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to a migrated disposable PostgreSQL database",
)


def test_postgres_case_insensitive_email_index_and_order_constraints(db_session):
    index_definition = db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_users_email_lower'")
    ).scalar_one()
    assert "UNIQUE INDEX" in index_definition.upper()
    assert "lower(" in index_definition and "email" in index_definition

    user = User(email="Case-Sensitive@example.test", password_hash="x", role=UserRole.PLAYER)
    db_session.add(user)
    db_session.commit()
    db_session.add(User(email="case-sensitive@example.test", password_hash="x", role=UserRole.PLAYER))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    coach, player, package = setup_pair(db_session, suffix="constraints")
    quote = player_quotation(db_session, player, package.id)
    order = accept_quotation(db_session, player, quote.id)
    second_quote = player_quotation(db_session, player, package.id)
    duplicate_ref = Order(
        quotation_id=second_quote.id,
        order_reference=order.order_reference,
        package_title=second_quote.package_title,
        package_description=second_quote.package_description,
        price_amount=second_quote.price_amount,
        currency=second_quote.currency,
        session_limit=second_quote.session_limit,
        duration_days=second_quote.duration_days,
        terms=second_quote.terms,
    )
    db_session.add(duplicate_ref)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(func.count(Order.id))) == 1

    db_session.add(CoachingPackage(
        coach_profile_id=uuid4(), title="Invalid FK", description="x", price_amount=Decimal("1.00"),
        currency="USD", session_limit=1, duration_days=1,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_postgres_expiry_rolls_back_order_creation(db_session):
    _, player, package = setup_pair(db_session, suffix="expiry")
    quote = player_quotation(db_session, player, package.id)
    from app.models.commerce import Quotation

    stored_quote = db_session.get(Quotation, quote.id)
    now = datetime.now(UTC)
    stored_quote.created_at = now - timedelta(minutes=2)
    stored_quote.expires_at = now - timedelta(minutes=1)
    db_session.commit()
    with pytest.raises(CommerceError) as error:
        accept_quotation(db_session, player, quote.id)
    assert error.value.status_code == 409
    assert db_session.scalar(select(func.count(Order.id))) == 0


def test_postgres_concurrent_acceptance_creates_only_one_order(db_session):
    _, player, package = setup_pair(db_session, suffix="concurrent")
    quote = player_quotation(db_session, player, package.id)
    session_factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    barrier = Barrier(2)

    def attempt_acceptance():
        with session_factory() as session:
            current_player = session.get(User, player.id)
            barrier.wait(timeout=10)
            try:
                return accept_quotation(session, current_player, quote.id).id
            except CommerceError as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt_acceptance(), range(2)))
    assert sum(isinstance(result, type(uuid4())) for result in outcomes) == 1
    assert outcomes.count(409) == 1
    assert db_session.scalar(select(func.count(Order.id))) == 1
