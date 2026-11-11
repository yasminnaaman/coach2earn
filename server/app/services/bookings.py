"""Availability, booking and coaching session business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.commerce import Booking, CoachAvailability, CoachingSession, Order
from app.models.enums import BookingStatus, OrderStatus, SessionStatus
from app.models.identity import CoachProfile, PlayerProfile, User
from app.schemas.bookings import (
    AvailabilityRead,
    AvailabilityWrite,
    AvailableSlot,
    BookingCreate,
    BookingRead,
    BookingStatusUpdate,
    SessionRead,
    SessionStatusUpdate,
)


class BookingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HMM_FMT = "%H:%M"


def _parse_hm(value: str) -> tuple[int, int]:
    dt = datetime.strptime(value, _HMM_FMT)
    return dt.hour, dt.minute


def _serialize_availability(av: CoachAvailability) -> AvailabilityRead:
    return AvailabilityRead(
        id=av.id,
        coach_profile_id=av.coach_profile_id,
        weekday=av.weekday,
        specific_date=av.specific_date,
        starts_at_utc=av.starts_at_utc,
        ends_at_utc=av.ends_at_utc,
        slot_duration_minutes=av.slot_duration_minutes,
        is_active=av.is_active,
        created_at=av.created_at,
        updated_at=av.updated_at,
    )


def _serialize_session(s: CoachingSession) -> SessionRead:
    return SessionRead(
        id=s.id,
        booking_id=s.booking_id,
        sequence_number=s.sequence_number,
        starts_at=s.starts_at,
        ends_at=s.ends_at,
        status=s.status.value,
        confirmed_at=s.confirmed_at,
        completed_at=s.completed_at,
        cancelled_at=s.cancelled_at,
        coach_notes=s.coach_notes,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _serialize_booking(booking: Booking) -> BookingRead:
    return BookingRead(
        id=booking.id,
        order_id=booking.order_id,
        status=booking.status.value,
        confirmed_at=booking.confirmed_at,
        cancelled_at=booking.cancelled_at,
        completed_at=booking.completed_at,
        sessions=[_serialize_session(s) for s in booking.sessions],
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )


def _coach_for_user(user: User) -> CoachProfile:
    if user.coach_profile is None:
        raise BookingError("Coach profile not found", 404)
    return user.coach_profile


def _player_for_user(user: User) -> PlayerProfile:
    if user.player_profile is None:
        raise BookingError("Player profile not found", 404)
    return user.player_profile


# ---------------------------------------------------------------------------
# Coach availability
# ---------------------------------------------------------------------------

def list_availability(db: Session, coach_profile_id: UUID) -> list[AvailabilityRead]:
    rows = list(
        db.scalars(
            select(CoachAvailability)
            .where(
                CoachAvailability.coach_profile_id == coach_profile_id,
                CoachAvailability.is_active.is_(True),
            )
            .order_by(CoachAvailability.weekday.nulls_last(), CoachAvailability.specific_date)
        )
    )
    return [_serialize_availability(av) for av in rows]


def create_availability(
    db: Session, user: User, payload: AvailabilityWrite
) -> AvailabilityRead:
    coach = _coach_for_user(user)
    av = CoachAvailability(
        coach_profile_id=coach.id,
        weekday=payload.weekday,
        specific_date=payload.specific_date,
        starts_at_utc=payload.starts_at_utc,
        ends_at_utc=payload.ends_at_utc,
        slot_duration_minutes=payload.slot_duration_minutes,
        is_active=payload.is_active,
    )
    db.add(av)
    db.commit()
    db.refresh(av)
    return _serialize_availability(av)


def update_availability(
    db: Session, user: User, availability_id: UUID, payload: AvailabilityWrite
) -> AvailabilityRead:
    coach = _coach_for_user(user)
    av = db.get(CoachAvailability, availability_id)
    if av is None or av.coach_profile_id != coach.id:
        raise BookingError("Availability record not found", 404)
    av.weekday = payload.weekday
    av.specific_date = payload.specific_date
    av.starts_at_utc = payload.starts_at_utc
    av.ends_at_utc = payload.ends_at_utc
    av.slot_duration_minutes = payload.slot_duration_minutes
    av.is_active = payload.is_active
    av.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(av)
    return _serialize_availability(av)


def delete_availability(db: Session, user: User, availability_id: UUID) -> None:
    coach = _coach_for_user(user)
    av = db.get(CoachAvailability, availability_id)
    if av is None or av.coach_profile_id != coach.id:
        raise BookingError("Availability record not found", 404)
    # Soft-delete to preserve historical references
    av.is_active = False
    av.updated_at = datetime.now(UTC)
    db.commit()


# ---------------------------------------------------------------------------
# Available slot enumeration
# ---------------------------------------------------------------------------

def _slots_for_window(
    av: CoachAvailability,
    date: datetime,
    booked_windows: list[tuple[datetime, datetime]],
) -> list[AvailableSlot]:
    """Expand a single availability window on a specific calendar date into slots."""
    sh, sm = _parse_hm(av.starts_at_utc)
    eh, em = _parse_hm(av.ends_at_utc)
    window_start = date.replace(hour=sh, minute=sm, second=0, microsecond=0, tzinfo=UTC)
    window_end = date.replace(hour=eh, minute=em, second=0, microsecond=0, tzinfo=UTC)
    slot_len = timedelta(minutes=av.slot_duration_minutes)
    slots: list[AvailableSlot] = []
    cursor = window_start
    while cursor + slot_len <= window_end:
        slot_end = cursor + slot_len
        # Skip if overlaps any existing booking
        overlaps = any(
            not (slot_end <= bstart or cursor >= bend)
            for bstart, bend in booked_windows
        )
        if not overlaps:
            slots.append(AvailableSlot(starts_at=cursor, ends_at=slot_end, availability_id=av.id))
        cursor = slot_end
    return slots


def available_slots(
    db: Session,
    coach_profile_id: UUID,
    from_dt: datetime,
    to_dt: datetime,
) -> list[AvailableSlot]:
    """Return all open slots for a coach between from_dt and to_dt (UTC)."""
    availability = list(
        db.scalars(
            select(CoachAvailability).where(
                CoachAvailability.coach_profile_id == coach_profile_id,
                CoachAvailability.is_active.is_(True),
            )
        )
    )
    # Collect already-booked intervals in the range
    booked = list(
        db.scalars(
            select(CoachingSession)
            .join(CoachingSession.booking)
            .join(Booking.order)
            .where(
                Order.quotation.has(coach_profile_id=coach_profile_id),
                CoachingSession.status.notin_([SessionStatus.CANCELLED]),
                CoachingSession.starts_at >= from_dt,
                CoachingSession.starts_at < to_dt,
            )
        )
    )
    booked_windows = [(s.starts_at, s.ends_at) for s in booked]

    results: list[AvailableSlot] = []
    current = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while current < to_dt:
        day_iso = current.isoweekday()  # 1=Mon…7=Sun
        for av in availability:
            if av.weekday is not None and av.weekday == day_iso:
                results.extend(_slots_for_window(av, current, booked_windows))
            elif av.specific_date is not None:
                specific = av.specific_date.replace(tzinfo=UTC) if av.specific_date.tzinfo is None else av.specific_date
                if specific.date() == current.date():
                    results.extend(_slots_for_window(av, current, booked_windows))
        current += timedelta(days=1)

    results.sort(key=lambda s: s.starts_at)
    return results


# ---------------------------------------------------------------------------
# Booking creation
# ---------------------------------------------------------------------------

def _order_for_player(db: Session, user: User, order_id: UUID) -> Order:
    player = _player_for_user(user)
    order = db.scalar(
        select(Order)
        .options(joinedload(Order.quotation))
        .where(Order.id == order_id)
        .with_for_update()
    )
    if order is None or order.quotation.player_profile_id != player.id:
        raise BookingError("Order not found", 404)
    return order


def create_booking(db: Session, user: User, payload: BookingCreate) -> BookingRead:
    """Create the first (sequence 1) session for a confirmed order."""
    order = _order_for_player(db, user, payload.order_id)

    if order.status != OrderStatus.CONFIRMED:
        raise BookingError("Order must be confirmed (paid) before booking", 409)
    if order.booking is not None:
        raise BookingError("A booking already exists for this order", 409)

    coach_profile_id: UUID = order.quotation.coach_profile_id

    # Validate requested slot does not overlap existing bookings
    requested_end = payload.starts_at + timedelta(minutes=60)  # default 1-hour slot
    conflicts = list(
        db.scalars(
            select(CoachingSession)
            .join(CoachingSession.booking)
            .join(Booking.order)
            .where(
                Order.quotation.has(coach_profile_id=coach_profile_id),
                CoachingSession.status.notin_([SessionStatus.CANCELLED]),
                CoachingSession.starts_at < requested_end,
                CoachingSession.ends_at > payload.starts_at,
            )
        )
    )
    if conflicts:
        raise BookingError("The requested time slot is not available", 409)

    booking = Booking(order=order, status=BookingStatus.PENDING)
    session = CoachingSession(
        booking=booking,
        sequence_number=1,
        starts_at=payload.starts_at,
        ends_at=requested_end,
        status=SessionStatus.SCHEDULED,
        coach_notes=payload.notes,
    )
    db.add(booking)
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BookingError("A booking already exists for this order", 409) from None
    db.refresh(booking)
    return _serialize_booking(booking)


# ---------------------------------------------------------------------------
# Booking retrieval
# ---------------------------------------------------------------------------

def get_booking(db: Session, user: User, booking_id: UUID) -> BookingRead:
    booking = db.scalar(
        select(Booking)
        .options(selectinload(Booking.sessions))
        .where(Booking.id == booking_id)
    )
    if booking is None:
        raise BookingError("Booking not found", 404)
    _assert_booking_access(user, booking)
    return _serialize_booking(booking)


def list_bookings(db: Session, user: User) -> list[BookingRead]:
    from app.models.commerce import Quotation  # local to avoid circular

    if user.coach_profile is not None:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.sessions))
            .join(Booking.order)
            .join(Order.quotation)
            .where(Quotation.coach_profile_id == user.coach_profile.id)
            .order_by(Booking.created_at.desc())
        )
    elif user.player_profile is not None:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.sessions))
            .join(Booking.order)
            .join(Order.quotation)
            .where(Quotation.player_profile_id == user.player_profile.id)
            .order_by(Booking.created_at.desc())
        )
    else:
        raise BookingError("Profile not found", 404)
    return [_serialize_booking(b) for b in db.scalars(stmt)]


def _assert_booking_access(user: User, booking: Booking) -> None:
    from app.models.commerce import Quotation  # local to avoid circular

    order = booking.order
    if order is None:
        # lazy-load
        raise BookingError("Booking not found", 404)
    quote = order.quotation
    if user.role.value == "admin":
        return
    if user.player_profile and quote.player_profile_id == user.player_profile.id:
        return
    if user.coach_profile and quote.coach_profile_id == user.coach_profile.id:
        return
    raise BookingError("Booking not found", 404)


# ---------------------------------------------------------------------------
# Booking state transitions
# ---------------------------------------------------------------------------

_BOOKING_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.COMPLETED: set(),
    BookingStatus.CANCELLED: set(),
}


def update_booking_status(
    db: Session, user: User, booking_id: UUID, payload: BookingStatusUpdate
) -> BookingRead:
    booking = db.scalar(
        select(Booking)
        .options(selectinload(Booking.sessions))
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    if booking is None:
        raise BookingError("Booking not found", 404)
    _assert_booking_access(user, booking)

    target = BookingStatus(payload.status)
    if target not in _BOOKING_TRANSITIONS.get(booking.status, set()):
        raise BookingError(
            f"Cannot transition booking from {booking.status.value} to {payload.status}", 409
        )

    now = datetime.now(UTC)
    booking.status = target
    if target == BookingStatus.CONFIRMED:
        booking.confirmed_at = now
    elif target == BookingStatus.CANCELLED:
        booking.cancelled_at = now
    elif target == BookingStatus.COMPLETED:
        booking.completed_at = now
    booking.updated_at = now
    db.commit()
    db.refresh(booking)
    return _serialize_booking(booking)


# ---------------------------------------------------------------------------
# Session state transitions
# ---------------------------------------------------------------------------

_SESSION_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.SCHEDULED: {SessionStatus.CONFIRMED, SessionStatus.CANCELLED},
    SessionStatus.CONFIRMED: {SessionStatus.COMPLETED, SessionStatus.CANCELLED},
    SessionStatus.COMPLETED: set(),
    SessionStatus.CANCELLED: set(),
    SessionStatus.DISPUTED: {SessionStatus.COMPLETED, SessionStatus.CANCELLED},
}


def update_session_status(
    db: Session, user: User, booking_id: UUID, session_id: UUID, payload: SessionStatusUpdate
) -> SessionRead:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id)
    )
    if booking is None:
        raise BookingError("Booking not found", 404)
    _assert_booking_access(user, booking)

    session = db.scalar(
        select(CoachingSession).where(
            CoachingSession.id == session_id,
            CoachingSession.booking_id == booking_id,
        ).with_for_update()
    )
    if session is None:
        raise BookingError("Session not found", 404)

    target = SessionStatus(payload.status)
    if target not in _SESSION_TRANSITIONS.get(session.status, set()):
        raise BookingError(
            f"Cannot transition session from {session.status.value} to {payload.status}", 409
        )

    now = datetime.now(UTC)
    session.status = target
    if target == SessionStatus.CONFIRMED:
        session.confirmed_at = now
    elif target == SessionStatus.COMPLETED:
        session.completed_at = now
    elif target == SessionStatus.CANCELLED:
        session.cancelled_at = now
    if payload.coach_notes is not None:
        session.coach_notes = payload.coach_notes
    session.updated_at = now
    db.commit()
    db.refresh(session)
    return _serialize_session(session)
