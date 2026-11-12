"""Availability, slot enumeration and booking lifecycle integration tests."""

from datetime import UTC, datetime, date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.commerce import CoachAvailability, CoachingPackage
from app.models.enums import OrderStatus, UserRole, VerificationStatus
from app.models.identity import CoachProfile, CoachSpecialisation, PlayerProfile, Specialisation, User
from app.seed_specialisations import seed_specialisations


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _user(db, role, email, **kwargs):
    u = User(email=email, password_hash="x", role=role, date_of_birth=date(1990, 1, 1), **kwargs)
    db.add(u)
    db.commit()
    return u


def _headers(obj):
    return {"Authorization": f"Bearer {create_access_token(obj.id)}"}


def _setup_coach_player(db):
    seed_specialisations(db)
    spec = db.scalar(select(Specialisation).where(Specialisation.slug == "rocket-league"))
    coach = User(
        email="avail-coach@test.local", password_hash="x",
        role=UserRole.COACH, date_of_birth=date(1990, 1, 1),
        coach_profile=CoachProfile(
            professional_bio="Pro coach", experience_years=3,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    player = User(
        email="avail-player@test.local", password_hash="x",
        role=UserRole.PLAYER, date_of_birth=date(1995, 6, 1),
        player_profile=PlayerProfile(),
    )
    db.add_all([coach, player])
    db.commit()
    pkg = CoachingPackage(
        coach_profile_id=coach.coach_profile.id,
        title="Booking package",
        description="Desc",
        price_amount=Decimal("50.00"),
        currency="USD",
        session_limit=5,
        duration_days=30,
        terms="",
    )
    db.add(pkg)
    db.commit()
    return coach, player, pkg


# ---------------------------------------------------------------------------
# Availability CRUD
# ---------------------------------------------------------------------------

def test_availability_create_list_update_delete(api_client, db_session):
    coach, player, _ = _setup_coach_player(db_session)

    # Anonymous user cannot create availability
    anon = api_client.post("/api/v1/coaches/me/availability", json={
        "weekday": 1, "starts_at_utc": "09:00", "ends_at_utc": "17:00",
        "slot_duration_minutes": 60,
    })
    assert anon.status_code == 401

    # Player cannot create availability
    player_resp = api_client.post(
        "/api/v1/coaches/me/availability",
        headers=_headers(player),
        json={"weekday": 1, "starts_at_utc": "09:00", "ends_at_utc": "17:00",
              "slot_duration_minutes": 60},
    )
    assert player_resp.status_code == 403

    # Coach creates recurring (weekday) availability
    resp = api_client.post(
        "/api/v1/coaches/me/availability",
        headers=_headers(coach),
        json={"weekday": 1, "starts_at_utc": "09:00", "ends_at_utc": "11:00",
              "slot_duration_minutes": 60},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    av_id = data["id"]
    assert data["weekday"] == 1
    assert data["coach_profile_id"] == str(coach.coach_profile.id)

    # Providing both weekday and specific_date is invalid
    bad = api_client.post(
        "/api/v1/coaches/me/availability",
        headers=_headers(coach),
        json={"weekday": 1, "specific_date": "2026-12-01T10:00:00Z",
              "starts_at_utc": "09:00", "ends_at_utc": "11:00",
              "slot_duration_minutes": 60},
    )
    assert bad.status_code == 422

    # List shows the created record
    listed = api_client.get(f"/api/v1/coaches/{coach.coach_profile.id}/availability")
    assert listed.status_code == 200
    assert any(a["id"] == av_id for a in listed.json())

    # Update
    upd = api_client.put(
        f"/api/v1/coaches/me/availability/{av_id}",
        headers=_headers(coach),
        json={"weekday": 2, "starts_at_utc": "10:00", "ends_at_utc": "12:00",
              "slot_duration_minutes": 60},
    )
    assert upd.status_code == 200 and upd.json()["weekday"] == 2

    # Another coach cannot update it
    other_coach = _user(
        db_session, UserRole.COACH, "other-coach@test.local",
        coach_profile=CoachProfile(professional_bio="Other", experience_years=1),
    )
    stranger = api_client.put(
        f"/api/v1/coaches/me/availability/{av_id}",
        headers=_headers(other_coach),
        json={"weekday": 3, "starts_at_utc": "10:00", "ends_at_utc": "12:00",
              "slot_duration_minutes": 60},
    )
    assert stranger.status_code == 404

    # Soft-delete
    del_resp = api_client.delete(
        f"/api/v1/coaches/me/availability/{av_id}", headers=_headers(coach)
    )
    assert del_resp.status_code == 204

    # No longer listed after deletion
    after = api_client.get(f"/api/v1/coaches/{coach.coach_profile.id}/availability")
    assert not any(a["id"] == av_id for a in after.json())


# ---------------------------------------------------------------------------
# Slot enumeration
# ---------------------------------------------------------------------------

def test_slots_expand_correctly(api_client, db_session):
    coach, _, _ = _setup_coach_player(db_session)

    # Create a Monday window: 09:00–11:00 UTC, 60-min slots → 2 slots
    api_client.post(
        "/api/v1/coaches/me/availability",
        headers=_headers(coach),
        json={"weekday": 1, "starts_at_utc": "09:00", "ends_at_utc": "11:00",
              "slot_duration_minutes": 60},
    )

    # Next Monday
    today = datetime.now(UTC).date()
    days_ahead = (7 - today.weekday()) % 7 or 7  # next Monday (weekday 0)
    next_monday = today + timedelta(days=days_ahead)
    from_dt = datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0, tzinfo=UTC).isoformat()
    to_dt = datetime(next_monday.year, next_monday.month, next_monday.day, 23, 59, 59, tzinfo=UTC).isoformat()

    slots = api_client.get(
        f"/api/v1/coaches/{coach.coach_profile.id}/slots",
        params={"from_dt": from_dt, "to_dt": to_dt},
    )
    assert slots.status_code == 200
    data = slots.json()
    assert len(data) == 2
    assert data[0]["starts_at"].endswith(("09:00:00+00:00", "09:00:00Z", "T09:00:00"))


def test_slots_range_validation(api_client, db_session):
    coach, _, _ = _setup_coach_player(db_session)
    now = datetime.now(UTC)

    # to_dt before from_dt
    bad = api_client.get(
        f"/api/v1/coaches/{coach.coach_profile.id}/slots",
        params={
            "from_dt": (now + timedelta(days=5)).isoformat(),
            "to_dt": now.isoformat(),
        },
    )
    assert bad.status_code == 422

    # Range > 60 days
    big = api_client.get(
        f"/api/v1/coaches/{coach.coach_profile.id}/slots",
        params={
            "from_dt": now.isoformat(),
            "to_dt": (now + timedelta(days=61)).isoformat(),
        },
    )
    assert big.status_code == 422


# ---------------------------------------------------------------------------
# Booking lifecycle
# ---------------------------------------------------------------------------

def _create_confirmed_order(api_client, db_session, coach, player, pkg):
    """Create a quotation and accept it, then mark the order CONFIRMED directly."""
    quote_resp = api_client.post(
        "/api/v1/quotations",
        headers=_headers(player),
        json={"package_id": str(pkg.id)},
    )
    assert quote_resp.status_code == 201, quote_resp.text
    order_resp = api_client.post(
        "/api/v1/orders",
        headers=_headers(player),
        json={"quotation_id": quote_resp.json()["id"]},
    )
    assert order_resp.status_code == 201, order_resp.text
    order_id = order_resp.json()["id"]

    # Simulate payment confirmation by setting order status directly (payment owner updates this)
    from uuid import UUID as _UUID
    from app.models.commerce import Order
    order = db_session.get(Order, _UUID(order_id))
    order.status = OrderStatus.CONFIRMED
    db_session.commit()
    return order_id


def test_booking_create_and_status_transitions(api_client, db_session):
    coach, player, pkg = _setup_coach_player(db_session)
    order_id = _create_confirmed_order(api_client, db_session, coach, player, pkg)

    starts_at = (datetime.now(UTC) + timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0
    ).isoformat()

    # Create booking
    resp = api_client.post(
        "/api/v1/bookings",
        headers=_headers(player),
        json={"order_id": order_id, "starts_at": starts_at},
    )
    assert resp.status_code == 201, resp.text
    booking = resp.json()
    booking_id = booking["id"]
    assert booking["status"] == "pending"
    assert len(booking["sessions"]) == 1
    assert booking["sessions"][0]["status"] == "scheduled"

    # Duplicate booking on same order is rejected
    dup = api_client.post(
        "/api/v1/bookings",
        headers=_headers(player),
        json={"order_id": order_id, "starts_at": starts_at},
    )
    assert dup.status_code == 409

    # Coach confirms the booking
    confirm = api_client.patch(
        f"/api/v1/bookings/{booking_id}/status",
        headers=_headers(coach),
        json={"status": "confirmed"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    assert confirm.json()["confirmed_at"] is not None

    # Coach completes it
    complete = api_client.patch(
        f"/api/v1/bookings/{booking_id}/status",
        headers=_headers(coach),
        json={"status": "completed"},
    )
    assert complete.status_code == 200 and complete.json()["status"] == "completed"

    # Cannot transition from completed
    bad_trans = api_client.patch(
        f"/api/v1/bookings/{booking_id}/status",
        headers=_headers(coach),
        json={"status": "cancelled"},
    )
    assert bad_trans.status_code == 409


def test_booking_requires_confirmed_order(api_client, db_session):
    """Booking a PENDING_PAYMENT order must be rejected."""
    coach, player, pkg = _setup_coach_player(db_session)

    quote_resp = api_client.post(
        "/api/v1/quotations",
        headers=_headers(player),
        json={"package_id": str(pkg.id)},
    )
    order_resp = api_client.post(
        "/api/v1/orders",
        headers=_headers(player),
        json={"quotation_id": quote_resp.json()["id"]},
    )
    order_id = order_resp.json()["id"]
    starts_at = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    resp = api_client.post(
        "/api/v1/bookings",
        headers=_headers(player),
        json={"order_id": order_id, "starts_at": starts_at},
    )
    assert resp.status_code == 409


def test_booking_visibility_permissions(api_client, db_session):
    """A player cannot view another player's booking."""
    coach, player, pkg = _setup_coach_player(db_session)
    order_id = _create_confirmed_order(api_client, db_session, coach, player, pkg)
    starts_at = (datetime.now(UTC) + timedelta(days=4)).replace(
        hour=14, minute=0, second=0, microsecond=0
    ).isoformat()

    create_resp = api_client.post(
        "/api/v1/bookings",
        headers=_headers(player),
        json={"order_id": order_id, "starts_at": starts_at},
    )
    assert create_resp.status_code == 201
    booking_id = create_resp.json()["id"]

    stranger = _user(
        db_session, UserRole.PLAYER, "stranger-booking@test.local",
        player_profile=PlayerProfile(),
    )

    # Stranger cannot read the booking
    assert api_client.get(
        f"/api/v1/bookings/{booking_id}", headers=_headers(stranger)
    ).status_code == 404

    # Coach can read it
    assert api_client.get(
        f"/api/v1/bookings/{booking_id}", headers=_headers(coach)
    ).status_code == 200

    # List – player sees their own
    player_list = api_client.get("/api/v1/bookings", headers=_headers(player))
    assert player_list.status_code == 200
    assert any(b["id"] == booking_id for b in player_list.json())

    # Unauthenticated access denied
    assert api_client.get(f"/api/v1/bookings/{booking_id}").status_code == 401


def test_session_status_transition(api_client, db_session):
    coach, player, pkg = _setup_coach_player(db_session)
    order_id = _create_confirmed_order(api_client, db_session, coach, player, pkg)
    starts_at = (datetime.now(UTC) + timedelta(days=5)).replace(
        hour=9, minute=0, second=0, microsecond=0
    ).isoformat()

    booking_resp = api_client.post(
        "/api/v1/bookings",
        headers=_headers(player),
        json={"order_id": order_id, "starts_at": starts_at},
    )
    assert booking_resp.status_code == 201
    booking_id = booking_resp.json()["id"]
    session_id = booking_resp.json()["sessions"][0]["id"]

    # Coach confirms session
    s_confirm = api_client.patch(
        f"/api/v1/bookings/{booking_id}/sessions/{session_id}/status",
        headers=_headers(coach),
        json={"status": "confirmed", "coach_notes": "See you then!"},
    )
    assert s_confirm.status_code == 200
    assert s_confirm.json()["status"] == "confirmed"
    assert s_confirm.json()["coach_notes"] == "See you then!"

    # Coach completes session
    s_complete = api_client.patch(
        f"/api/v1/bookings/{booking_id}/sessions/{session_id}/status",
        headers=_headers(coach),
        json={"status": "completed"},
    )
    assert s_complete.status_code == 200
    assert s_complete.json()["completed_at"] is not None

    # Cannot cancel a completed session
    s_bad = api_client.patch(
        f"/api/v1/bookings/{booking_id}/sessions/{session_id}/status",
        headers=_headers(coach),
        json={"status": "cancelled"},
    )
    assert s_bad.status_code == 409
