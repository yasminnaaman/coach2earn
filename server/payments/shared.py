"""Shared payment hooks called by Hope's backend and Yasmin's AI layer.

Exported from payments/__init__.py as the agreed API:
  - create_booked_sessions(db, order_id)
  - get_confirmed_unpaid_sessions(db)
  - release_bonus(db, prize_id)

Handoff agreed with Hope at the 10% mark.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.commerce import Booking, CoachingSession, Order, Quotation
from app.models.enums import BookingStatus, BonusStatus, EarningStatus, OrderStatus, PayoutStatus, PrizeStatus, SessionStatus
from app.models.finance import CoachEarning, PayoutRecord
from app.models.rewards import Bonus, Prize

log = logging.getLogger(__name__)

# Platform commission rate (8%)
PLATFORM_FEE_RATE = Decimal("0.08")


def create_booked_sessions(db: Session, order_id: UUID) -> Booking:
    """Called by POST /payments/orders/{id}/capture after successful PayPal capture.

    Marks the order CONFIRMED and creates a pending Booking so the team can
    schedule individual sessions. Does nothing if a booking already exists
    (idempotent).
    """
    order = db.scalar(
        select(Order)
        .options(joinedload(Order.quotation), joinedload(Order.booking))
        .where(Order.id == order_id)
        .with_for_update()
    )
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    if order.booking is not None:
        log.info("create_booked_sessions: booking already exists for order %s — skipping", order_id)
        return order.booking

    order.status = OrderStatus.CONFIRMED
    booking = Booking(order=order, status=BookingStatus.PENDING)
    db.add(booking)

    # Accrue the coach's gross earning for this order (net of platform fee)
    gross = order.price_amount
    commission = (gross * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
    net = gross - commission
    earning = CoachEarning(
        coach_profile_id=order.quotation.coach_profile_id,
        order_id=order.id,
        gross_amount=gross,
        commission_amount=commission,
        net_amount=net,
        currency=order.currency,
        status=EarningStatus.PENDING,
    )
    db.add(earning)
    db.commit()
    db.refresh(booking)
    return booking


def get_confirmed_unpaid_sessions(db: Session) -> list[dict]:
    """Return all confirmed coaching sessions whose earnings have not yet been paid.

    Called by POST /payments/payouts/run to build the Payouts batch.
    Each item contains: session_id, coach_profile_id, coach_email, net_amount, currency.
    """
    from app.models.identity import CoachProfile, User  # local to avoid circular

    rows = db.execute(
        select(
            CoachingSession.id.label("session_id"),
            CoachEarning.id.label("earning_id"),
            CoachEarning.coach_profile_id,
            CoachEarning.net_amount,
            CoachEarning.currency,
            User.email,
        )
        .join(CoachingSession.earnings)
        .join(CoachEarning.coach_profile)
        .join(CoachProfile.user)
        .where(
            CoachingSession.status == SessionStatus.CONFIRMED,
            CoachEarning.status == EarningStatus.AVAILABLE,
        )
    ).fetchall()

    return [
        {
            "session_id": str(r.session_id),
            "earning_id": str(r.earning_id),
            "coach_profile_id": str(r.coach_profile_id),
            "recipient_email": r.email,
            "net_amount": str(r.net_amount),
            "currency": r.currency,
        }
        for r in rows
    ]


def release_bonus(db: Session, prize_id: UUID) -> list[Bonus]:
    """Called by POST /prizes/{id}/received when Hope marks a prize as received.

    Sets the prize status to RECEIVED and transitions all associated EARNED
    bonuses to RELEASED, then creates a PayoutRecord for each so Brian's
    payouts batch can pick them up.
    """
    prize = db.scalar(select(Prize).where(Prize.id == prize_id).with_for_update())
    if prize is None:
        raise ValueError(f"Prize {prize_id} not found")
    if prize.status not in (PrizeStatus.PENDING,):
        log.info("release_bonus: prize %s already processed (status=%s) — skipping", prize_id, prize.status)
        return []

    prize.status = PrizeStatus.RECEIVED
    released: list[Bonus] = []

    bonuses = list(db.scalars(select(Bonus).where(Bonus.prize_id == prize_id, Bonus.status == BonusStatus.EARNED)))
    for bonus in bonuses:
        bonus.status = BonusStatus.RELEASED
        # Create a payout record for Brian's batch
        payout = PayoutRecord(
            coach_profile_id=bonus.coach_profile_id,
            amount=bonus.bonus_amount,
            currency=bonus.currency,
            status=PayoutStatus.PENDING,
        )
        db.add(payout)
        released.append(bonus)

    db.commit()
    return released
