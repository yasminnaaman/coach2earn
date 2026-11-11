"""Coach availability, booking management and session scheduling endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_coach, require_player
from app.db.session import get_db
from app.models.identity import User
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
from app.services.bookings import (
    BookingError,
    available_slots,
    create_availability,
    create_booking,
    delete_availability,
    get_booking,
    list_availability,
    list_bookings,
    update_availability,
    update_booking_status,
    update_session_status,
)

router = APIRouter()


def _fail(exc: BookingError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Coach availability
# ---------------------------------------------------------------------------

@router.get(
    "/coaches/{coach_profile_id}/availability",
    response_model=list[AvailabilityRead],
    tags=["availability"],
    summary="List a coach's published availability windows",
)
def coach_availability(coach_profile_id: UUID, db: Session = Depends(get_db)) -> list[AvailabilityRead]:
    return list_availability(db, coach_profile_id)


@router.post(
    "/coaches/me/availability",
    response_model=AvailabilityRead,
    status_code=201,
    tags=["availability"],
    summary="Publish a new availability window",
)
def add_availability(
    payload: AvailabilityWrite,
    user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> AvailabilityRead:
    try:
        return create_availability(db, user, payload)
    except BookingError as exc:
        _fail(exc)


@router.put(
    "/coaches/me/availability/{availability_id}",
    response_model=AvailabilityRead,
    tags=["availability"],
    summary="Update an availability window",
)
def edit_availability(
    availability_id: UUID,
    payload: AvailabilityWrite,
    user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> AvailabilityRead:
    try:
        return update_availability(db, user, availability_id, payload)
    except BookingError as exc:
        _fail(exc)


@router.delete(
    "/coaches/me/availability/{availability_id}",
    status_code=204,
    tags=["availability"],
    summary="Remove (soft-delete) an availability window",
)
def remove_availability(
    availability_id: UUID,
    user: User = Depends(require_coach),
    db: Session = Depends(get_db),
) -> None:
    try:
        delete_availability(db, user, availability_id)
    except BookingError as exc:
        _fail(exc)


# ---------------------------------------------------------------------------
# Available slots
# ---------------------------------------------------------------------------

@router.get(
    "/coaches/{coach_profile_id}/slots",
    response_model=list[AvailableSlot],
    tags=["availability"],
    summary="List open booking slots for a coach in a date range",
)
def coach_slots(
    coach_profile_id: UUID,
    from_dt: datetime = Query(description="Range start in UTC ISO 8601"),
    to_dt: datetime = Query(description="Range end in UTC ISO 8601"),
    db: Session = Depends(get_db),
) -> list[AvailableSlot]:
    if to_dt <= from_dt:
        raise HTTPException(status_code=422, detail="to_dt must be after from_dt")
    delta = to_dt - from_dt
    if delta.days > 60:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 60 days")
    try:
        return available_slots(db, coach_profile_id, from_dt, to_dt)
    except BookingError as exc:
        _fail(exc)


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@router.post(
    "/bookings",
    response_model=BookingRead,
    status_code=201,
    tags=["bookings"],
    summary="Create a booking for a confirmed order",
)
def booking_create(
    payload: BookingCreate,
    user: User = Depends(require_player),
    db: Session = Depends(get_db),
) -> BookingRead:
    try:
        return create_booking(db, user, payload)
    except BookingError as exc:
        _fail(exc)


@router.get(
    "/bookings",
    response_model=list[BookingRead],
    tags=["bookings"],
    summary="List all bookings for the authenticated user",
)
def bookings_list(user: CurrentUser, db: Session = Depends(get_db)) -> list[BookingRead]:
    try:
        return list_bookings(db, user)
    except BookingError as exc:
        _fail(exc)


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingRead,
    tags=["bookings"],
    summary="Retrieve a single booking",
)
def booking_detail(
    booking_id: UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> BookingRead:
    try:
        return get_booking(db, user, booking_id)
    except BookingError as exc:
        _fail(exc)


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=BookingRead,
    tags=["bookings"],
    summary="Transition a booking status (confirm / cancel / complete)",
)
def booking_status(
    booking_id: UUID,
    payload: BookingStatusUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> BookingRead:
    try:
        return update_booking_status(db, user, booking_id, payload)
    except BookingError as exc:
        _fail(exc)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@router.patch(
    "/bookings/{booking_id}/sessions/{session_id}/status",
    response_model=SessionRead,
    tags=["sessions"],
    summary="Transition an individual session status",
)
def session_status(
    booking_id: UUID,
    session_id: UUID,
    payload: SessionStatusUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> SessionRead:
    try:
        return update_session_status(db, user, booking_id, session_id, payload)
    except BookingError as exc:
        _fail(exc)
