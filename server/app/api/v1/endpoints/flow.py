"""End-to-end prototype flow: simulated payment, scheduling, session lifecycle, messaging.

These endpoints complete the journey the frontend needs on top of the core
order/booking API (which is left unchanged):

    quote → order → POST /orders/{id}/pay (simulated) → POST /orders/{id}/sessions
    → coach: start → complete (+notes, earning recorded as pending)
    → player: confirm (earning released, points awarded) | dispute

Payments are SIMULATED — no money moves. This is clearly labelled in the UI.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import CurrentUser, require_coach, require_player
from app.db.session import get_db
from app.models.commerce import Booking, CoachingSession, Order, Quotation
from app.models.engagement import Message
from app.models.enums import (
    AccountStatus,
    BookingStatus,
    EarningStatus,
    OrderStatus,
    PointsSourceType,
    PointsTransactionType,
    SessionStatus,
    UserRole,
)
from app.models.finance import CoachEarning
from app.models.identity import CoachProfile, PlayerProfile, User
from app.models.rewards import PointsTransaction
from app.services.profiles import display_name_from_email

router = APIRouter()

COMMISSION_RATE = Decimal("0.15")
SESSION_MINUTES = 60
PLAYER_POINTS_PER_SESSION = 50
COACH_POINTS_PER_SESSION = 10  # 1 confirmed hour = 10 points (dashboard formula)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class PersonRef(BaseModel):
    user_id: UUID
    name: str
    coach_profile_id: UUID | None = None


class SessionItem(BaseModel):
    id: UUID
    booking_id: UUID
    order_id: UUID
    order_reference: str
    package_title: str
    sequence_number: int
    label: str
    starts_at: datetime
    ends_at: datetime
    status: str
    coach_notes: str | None
    player_confirmed: bool
    coach: PersonRef
    player: PersonRef


class OrderItem(BaseModel):
    order_id: UUID
    order_reference: str
    status: str
    package_title: str
    price_amount: Decimal
    currency: str
    session_limit: int
    remaining_to_schedule: int
    created_at: datetime
    coach: PersonRef
    player: PersonRef
    sessions: list[SessionItem]


class PayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_method: Literal["mpesa_sim", "card", "paypal_balance"]
    phone: str | None = Field(default=None, max_length=20)


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starts_at: list[datetime] = Field(min_length=1, max_length=50)


class CompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coach_notes: str | None = Field(default=None, max_length=4000)


class DisputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_user_id: UUID | None = None
    coach_profile_id: UUID | None = None
    order_id: UUID | None = None
    body: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    id: UUID
    sender_user_id: UUID
    recipient_user_id: UUID
    order_id: UUID | None
    body: str
    created_at: datetime
    read_at: datetime | None
    mine: bool


class ThreadRead(BaseModel):
    counterpart: PersonRef
    counterpart_role: str
    last_message: str
    last_at: datetime
    unread: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _person(user: User) -> PersonRef:
    return PersonRef(
        user_id=user.id,
        name=display_name_from_email(user.email),
        coach_profile_id=user.coach_profile.id if user.coach_profile else None,
    )


def _order_query():
    return select(Order).options(
        joinedload(Order.quotation).joinedload(Quotation.coach_profile).joinedload(CoachProfile.user),
        joinedload(Order.quotation).joinedload(Quotation.player_profile).joinedload(PlayerProfile.user),
        joinedload(Order.booking).selectinload(Booking.sessions).selectinload(CoachingSession.earnings),
    )


def _session_item(order: Order, session: CoachingSession) -> SessionItem:
    q = order.quotation
    return SessionItem(
        id=session.id,
        booking_id=session.booking_id,
        order_id=order.id,
        order_reference=order.order_reference,
        package_title=order.package_title,
        sequence_number=session.sequence_number,
        label=f"Session {session.sequence_number}",
        starts_at=_aware(session.starts_at),
        ends_at=_aware(session.ends_at),
        status=session.status.value,
        coach_notes=session.coach_notes,
        player_confirmed=any(e.status == EarningStatus.AVAILABLE for e in session.earnings),
        coach=_person(q.coach_profile.user),
        player=_person(q.player_profile.user),
    )


def _order_item(order: Order) -> OrderItem:
    q = order.quotation
    sessions = sorted(order.booking.sessions, key=lambda s: s.sequence_number) if order.booking else []
    live = [s for s in sessions if s.status != SessionStatus.CANCELLED]
    return OrderItem(
        order_id=order.id,
        order_reference=order.order_reference,
        status=order.status.value,
        package_title=order.package_title,
        price_amount=order.price_amount,
        currency=order.currency,
        session_limit=order.session_limit,
        remaining_to_schedule=max(0, order.session_limit - len(live)),
        created_at=_aware(order.created_at),
        coach=_person(q.coach_profile.user),
        player=_person(q.player_profile.user),
        sessions=[_session_item(order, s) for s in sessions],
    )


def _load_order(db: Session, order_id: UUID) -> Order:
    order = db.scalar(_order_query().where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _assert_player_owns(user: User, order: Order) -> None:
    if user.player_profile is None or order.quotation.player_profile_id != user.player_profile.id:
        raise HTTPException(status_code=404, detail="Order not found")


def _load_session(db: Session, user: User, session_id: UUID) -> tuple[Order, CoachingSession, str]:
    """Return (order, session, viewer) where viewer is 'coach' | 'player' | 'admin'."""
    session = db.scalar(
        select(CoachingSession)
        .options(selectinload(CoachingSession.earnings))
        .where(CoachingSession.id == session_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    order = _load_order(db, db.get(Booking, session.booking_id).order_id)
    q = order.quotation
    if user.coach_profile and q.coach_profile_id == user.coach_profile.id:
        return order, session, "coach"
    if user.player_profile and q.player_profile_id == user.player_profile.id:
        return order, session, "player"
    if user.role == UserRole.ADMIN:
        return order, session, "admin"
    raise HTTPException(status_code=404, detail="Session not found")


def _refresh_session_item(db: Session, order_id: UUID, session_id: UUID) -> SessionItem:
    db.expire_all()
    order = _load_order(db, order_id)
    session = next(s for s in order.booking.sessions if s.id == session_id)
    return _session_item(order, session)


# ─────────────────────────────────────────────────────────────────────────────
# Orders: simulated payment + listing + scheduling
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/pay", response_model=OrderItem, tags=["prototype flow"],
             summary="Simulated payment — marks a pending order as paid (no money moves)")
def pay_order(order_id: UUID, payload: PayRequest, user: User = Depends(require_player),
              db: Session = Depends(get_db)) -> OrderItem:
    order = _load_order(db, order_id)
    _assert_player_owns(user, order)
    if order.status == OrderStatus.PENDING_PAYMENT:
        order.status = OrderStatus.CONFIRMED
        db.commit()
    elif order.status not in {OrderStatus.CONFIRMED, OrderStatus.COMPLETED}:
        raise HTTPException(status_code=409, detail=f"Order cannot be paid (status {order.status.value})")
    db.expire_all()
    return _order_item(_load_order(db, order_id))


@router.get("/me/orders", response_model=list[OrderItem], tags=["prototype flow"],
            summary="Paid orders with their sessions, for the logged-in player or coach")
def my_orders(user: CurrentUser, db: Session = Depends(get_db)) -> list[OrderItem]:
    statement = _order_query().join(Order.quotation).where(
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.COMPLETED])
    )
    if user.coach_profile is not None:
        statement = statement.where(Quotation.coach_profile_id == user.coach_profile.id)
    elif user.player_profile is not None:
        statement = statement.where(Quotation.player_profile_id == user.player_profile.id)
    else:
        return []
    orders = db.scalars(statement.order_by(Order.created_at.desc())).unique().all()
    return [_order_item(o) for o in orders]


@router.get("/me/orders/{order_id}", response_model=OrderItem, tags=["prototype flow"])
def my_order(order_id: UUID, user: CurrentUser, db: Session = Depends(get_db)) -> OrderItem:
    order = _load_order(db, order_id)
    q = order.quotation
    allowed = (
        (user.player_profile and q.player_profile_id == user.player_profile.id)
        or (user.coach_profile and q.coach_profile_id == user.coach_profile.id)
        or user.role == UserRole.ADMIN
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_item(order)


@router.post("/orders/{order_id}/sessions", response_model=OrderItem, status_code=201,
             tags=["prototype flow"], summary="Schedule one or more sessions on a paid order")
def schedule_sessions(order_id: UUID, payload: ScheduleRequest, user: User = Depends(require_player),
                      db: Session = Depends(get_db)) -> OrderItem:
    order = _load_order(db, order_id)
    _assert_player_owns(user, order)
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Pay for the order before scheduling sessions")

    existing = list(order.booking.sessions) if order.booking else []
    live = [s for s in existing if s.status != SessionStatus.CANCELLED]
    if len(live) + len(payload.starts_at) > order.session_limit:
        raise HTTPException(
            status_code=409,
            detail=f"Only {order.session_limit - len(live)} session(s) left to schedule on this order",
        )

    now = datetime.now(UTC)
    starts = sorted(_aware(s) for s in payload.starts_at)
    for start in starts:
        if start <= now:
            raise HTTPException(status_code=422, detail="Sessions must be scheduled in the future")
    for a, b in zip(starts, starts[1:]):
        if b < a + timedelta(minutes=SESSION_MINUTES):
            raise HTTPException(status_code=422, detail="Requested sessions overlap each other")

    coach_profile_id = order.quotation.coach_profile_id
    for start in starts:
        end = start + timedelta(minutes=SESSION_MINUTES)
        clash = db.scalar(
            select(CoachingSession.id)
            .join(CoachingSession.booking)
            .join(Booking.order)
            .join(Order.quotation)
            .where(
                Quotation.coach_profile_id == coach_profile_id,
                CoachingSession.status != SessionStatus.CANCELLED,
                CoachingSession.starts_at < end,
                CoachingSession.ends_at > start,
            )
            .limit(1)
        )
        if clash is not None:
            raise HTTPException(
                status_code=409,
                detail=f"The coach is already booked at {start:%d %b %H:%M} UTC — pick another time",
            )

    booking = order.booking
    if booking is None:
        booking = Booking(id=uuid4(), order_id=order.id, status=BookingStatus.CONFIRMED, confirmed_at=now)
        db.add(booking)
        db.flush()
    next_seq = max((s.sequence_number for s in existing), default=0) + 1
    for offset, start in enumerate(starts):
        db.add(CoachingSession(
            id=uuid4(),
            booking_id=booking.id,
            sequence_number=next_seq + offset,
            starts_at=start,
            ends_at=start + timedelta(minutes=SESSION_MINUTES),
            status=SessionStatus.SCHEDULED,
        ))
    db.commit()
    db.expire_all()
    return _order_item(_load_order(db, order_id))


# ─────────────────────────────────────────────────────────────────────────────
# Session lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=SessionItem, tags=["prototype flow"])
def session_detail(session_id: UUID, user: CurrentUser, db: Session = Depends(get_db)) -> SessionItem:
    order, session, _viewer = _load_session(db, user, session_id)
    return _session_item(order, session)


@router.post("/sessions/{session_id}/start", response_model=SessionItem, tags=["prototype flow"],
             summary="Coach starts a scheduled session")
def start_session(session_id: UUID, user: User = Depends(require_coach),
                  db: Session = Depends(get_db)) -> SessionItem:
    order, session, viewer = _load_session(db, user, session_id)
    if viewer != "coach":
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail=f"Session is {session.status.value}, not scheduled")
    session.status = SessionStatus.CONFIRMED
    session.confirmed_at = datetime.now(UTC)
    db.commit()
    return _refresh_session_item(db, order.id, session_id)


@router.post("/sessions/{session_id}/complete", response_model=SessionItem, tags=["prototype flow"],
             summary="Coach ends a session, adds notes; earning is recorded pending player confirmation")
def complete_session(session_id: UUID, payload: CompleteRequest, user: User = Depends(require_coach),
                     db: Session = Depends(get_db)) -> SessionItem:
    order, session, viewer = _load_session(db, user, session_id)
    if viewer != "coach":
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in {SessionStatus.SCHEDULED, SessionStatus.CONFIRMED}:
        raise HTTPException(status_code=409, detail=f"Session is already {session.status.value}")
    now = datetime.now(UTC)
    session.status = SessionStatus.COMPLETED
    session.confirmed_at = session.confirmed_at or now
    session.completed_at = now
    if payload.coach_notes is not None and payload.coach_notes.strip():
        session.coach_notes = payload.coach_notes.strip()
    if not session.earnings:
        gross = (order.price_amount / order.session_limit).quantize(Decimal("0.01"))
        commission = (gross * COMMISSION_RATE).quantize(Decimal("0.01"))
        db.add(CoachEarning(
            id=uuid4(),
            coach_profile_id=order.quotation.coach_profile_id,
            order_id=order.id,
            session_id=session.id,
            gross_amount=gross,
            commission_amount=commission,
            net_amount=gross - commission,
            currency=order.currency,
            status=EarningStatus.PENDING,
        ))
    db.commit()
    return _refresh_session_item(db, order.id, session_id)


@router.post("/sessions/{session_id}/confirm", response_model=SessionItem, tags=["prototype flow"],
             summary="Player confirms a completed session — releases coach pay and awards points")
def confirm_session(session_id: UUID, user: User = Depends(require_player),
                    db: Session = Depends(get_db)) -> SessionItem:
    order, session, viewer = _load_session(db, user, session_id)
    if viewer != "player":
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in {SessionStatus.COMPLETED, SessionStatus.DISPUTED}:
        raise HTTPException(status_code=409, detail="Only completed sessions can be confirmed")
    if any(e.status == EarningStatus.AVAILABLE for e in session.earnings):
        raise HTTPException(status_code=409, detail="Session already confirmed")

    session.status = SessionStatus.COMPLETED
    for earning in session.earnings:
        earning.status = EarningStatus.AVAILABLE
    coach_user_id = order.quotation.coach_profile.user_id
    if db.scalar(select(PointsTransaction.id).where(PointsTransaction.session_id == session.id)) is None:
        db.add(PointsTransaction(
            id=uuid4(), user_id=user.id, session_id=session.id,
            transaction_type=PointsTransactionType.EARNED, source_type=PointsSourceType.SESSION,
            source_reference=f"session:{session.id}", points_delta=PLAYER_POINTS_PER_SESSION,
            description=f"Confirmed coaching session {session.sequence_number}.",
        ))
        db.add(PointsTransaction(
            id=uuid4(), user_id=coach_user_id, session_id=None,
            transaction_type=PointsTransactionType.EARNED, source_type=PointsSourceType.BONUS,
            source_reference=f"coach-session:{session.id}", points_delta=COACH_POINTS_PER_SESSION,
            description=f"Confirmed coaching hour (session {session.sequence_number}).",
        ))
    db.flush()

    # Close the order/booking once every session on it is confirmed.
    live = [s for s in order.booking.sessions if s.status != SessionStatus.CANCELLED]
    confirmed = [
        s for s in live
        if s.id == session.id or any(e.status == EarningStatus.AVAILABLE for e in s.earnings)
    ]
    if len(live) >= order.session_limit and len(confirmed) == len(live):
        order.status = OrderStatus.COMPLETED
        order.booking.status = BookingStatus.COMPLETED
        order.booking.completed_at = datetime.now(UTC)
    db.commit()
    return _refresh_session_item(db, order.id, session_id)


@router.post("/sessions/{session_id}/dispute", response_model=SessionItem, tags=["prototype flow"],
             summary="Player disputes a completed session — coach pay stays on hold")
def dispute_session(session_id: UUID, payload: DisputeRequest, user: User = Depends(require_player),
                    db: Session = Depends(get_db)) -> SessionItem:
    order, session, viewer = _load_session(db, user, session_id)
    if viewer != "player":
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.COMPLETED or any(
        e.status == EarningStatus.AVAILABLE for e in session.earnings
    ):
        raise HTTPException(status_code=409, detail="Only completed, unconfirmed sessions can be disputed")
    session.status = SessionStatus.DISPUTED
    db.add(Message(
        id=uuid4(), sender_user_id=user.id, recipient_user_id=order.quotation.coach_profile.user_id,
        order_id=order.id,
        body=f"⚠️ Dispute raised on Session {session.sequence_number}: {payload.reason.strip()}",
    ))
    db.commit()
    return _refresh_session_item(db, order.id, session_id)


@router.post("/sessions/{session_id}/cancel", response_model=SessionItem, tags=["prototype flow"],
             summary="Cancel a scheduled session (player or coach) — the slot can be rescheduled")
def cancel_session(session_id: UUID, user: CurrentUser, db: Session = Depends(get_db)) -> SessionItem:
    order, session, viewer = _load_session(db, user, session_id)
    if viewer not in {"coach", "player"}:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Only scheduled sessions can be cancelled")
    session.status = SessionStatus.CANCELLED
    session.cancelled_at = datetime.now(UTC)
    db.commit()
    return _refresh_session_item(db, order.id, session_id)


# ─────────────────────────────────────────────────────────────────────────────
# Messaging
# ─────────────────────────────────────────────────────────────────────────────

def _message_read(m: Message, me: UUID) -> MessageRead:
    return MessageRead(
        id=m.id, sender_user_id=m.sender_user_id, recipient_user_id=m.recipient_user_id,
        order_id=m.order_id, body=m.body, created_at=_aware(m.created_at),
        read_at=_aware(m.read_at) if m.read_at else None, mine=m.sender_user_id == me,
    )


@router.post("/messages", response_model=MessageRead, status_code=201, tags=["messages"])
def send_message(payload: MessageCreate, user: CurrentUser, db: Session = Depends(get_db)) -> MessageRead:
    recipient: User | None = None
    if payload.coach_profile_id is not None:
        profile = db.get(CoachProfile, payload.coach_profile_id)
        recipient = profile.user if profile else None
    elif payload.recipient_user_id is not None:
        recipient = db.get(User, payload.recipient_user_id)
    if recipient is None or recipient.account_status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if recipient.id == user.id:
        raise HTTPException(status_code=422, detail="You cannot message yourself")
    message = Message(
        id=uuid4(), sender_user_id=user.id, recipient_user_id=recipient.id,
        order_id=payload.order_id, body=payload.body.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return _message_read(message, user.id)


@router.get("/messages/threads", response_model=list[ThreadRead], tags=["messages"])
def message_threads(user: CurrentUser, db: Session = Depends(get_db)) -> list[ThreadRead]:
    messages = db.scalars(
        select(Message)
        .options(joinedload(Message.sender), joinedload(Message.recipient))
        .where(or_(Message.sender_user_id == user.id, Message.recipient_user_id == user.id))
        .order_by(Message.created_at.desc())
    ).all()
    threads: dict[UUID, ThreadRead] = {}
    for m in messages:
        other = m.recipient if m.sender_user_id == user.id else m.sender
        if other.id not in threads:
            threads[other.id] = ThreadRead(
                counterpart=_person(other), counterpart_role=other.role.value,
                last_message=m.body, last_at=_aware(m.created_at), unread=0,
            )
        if m.recipient_user_id == user.id and m.read_at is None:
            threads[other.id].unread += 1
    return list(threads.values())


@router.get("/messages/with/{user_id}", response_model=list[MessageRead], tags=["messages"])
def message_thread(user_id: UUID, user: CurrentUser, db: Session = Depends(get_db)) -> list[MessageRead]:
    messages = db.scalars(
        select(Message)
        .where(or_(
            (Message.sender_user_id == user.id) & (Message.recipient_user_id == user_id),
            (Message.sender_user_id == user_id) & (Message.recipient_user_id == user.id),
        ))
        .order_by(Message.created_at)
    ).all()
    now = datetime.now(UTC)
    changed = False
    for m in messages:
        if m.recipient_user_id == user.id and m.read_at is None:
            m.read_at = now
            changed = True
    if changed:
        db.commit()
    return [_message_read(m, user.id) for m in messages]


@router.get("/users/{user_id}/card", response_model=PersonRef, tags=["messages"],
            summary="Display name for a messaging counterpart")
def user_card(user_id: UUID, _user: CurrentUser, db: Session = Depends(get_db)) -> PersonRef:
    other = db.get(User, user_id)
    if other is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _person(other)
