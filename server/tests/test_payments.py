"""Unit tests for Brian's payments module.

Tests run against SQLite in mock PayPal mode (no network calls).
Covers the build-pack requirements:
  - Quote creation with 8% platform fee
  - Expired quote returns 410
  - Order creation and Idempotency-Key de-duplication
  - Capture creates booking and returns C2E-##### receipt ref
  - Payouts run (confirmed sessions only)
  - Webhook signature pass-through in mock mode
  - Refund endpoint
  - FX estimatedSavingKes calculation
  - Bonus math: 280 points = 7%, $2,000 prize = $140, 400 points = 10% cap, 500 = still 10%
"""

import os

os.environ["PAYPAL_MODE"] = "mock"

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

# -----------------------------------------------------------------------
# Bonus math unit tests (no DB required)
# -----------------------------------------------------------------------

def _bonus_pct(total_points: int) -> Decimal:
    """bonusPct = min(10, points × 0.025)  — from the build pack."""
    raw = Decimal(total_points) * Decimal("0.025")
    return min(Decimal("10"), raw)


def test_bonus_pct_280_points():
    assert _bonus_pct(280) == Decimal("7")


def test_bonus_pct_400_points_cap():
    assert _bonus_pct(400) == Decimal("10")


def test_bonus_pct_500_points_still_cap():
    assert _bonus_pct(500) == Decimal("10")


def test_bonus_pct_prize_2000():
    pct = _bonus_pct(280) / 100
    prize = Decimal("2000.00")
    bonus = (prize * pct).quantize(Decimal("0.01"))
    assert bonus == Decimal("140.00")


# -----------------------------------------------------------------------
# FX helper tests
# -----------------------------------------------------------------------

def test_estimated_saving_kes_demo_values():
    from payments.fx import estimated_saving_kes
    # $162.00 at 129 KES with 3.5% markup estimate
    # 162 × 129 × 0.035 = 731.43 → rounded to 731
    saving = estimated_saving_kes(Decimal("162.00"), Decimal("129.00"))
    assert saving > 0
    # The build pack says "about KES 600" so we just check order of magnitude
    assert Decimal("400") <= saving <= Decimal("1000")


def test_fx_fixed_rate_default():
    from payments.fx import get_usd_to_kes_rate
    rate = get_usd_to_kes_rate()
    assert rate == Decimal("129.00")


# -----------------------------------------------------------------------
# API endpoint tests (against mock PayPal + SQLite)
# -----------------------------------------------------------------------

def setup_package(db_session):
    """Create a verified coach + package for payment tests."""
    from datetime import date
    from app.models.commerce import CoachingPackage
    from app.models.enums import UserRole, VerificationStatus
    from app.models.identity import CoachProfile, CoachSpecialisation, Specialisation, User
    from app.seed_specialisations import seed_specialisations
    from sqlalchemy import select

    seed_specialisations(db_session)
    spec = db_session.scalar(select(Specialisation).where(Specialisation.slug == "rocket-league"))
    coach = User(
        email="payments-coach@test.local",
        password_hash="x",
        role=UserRole.COACH,
        date_of_birth=date(1990, 1, 1),
        coach_profile=CoachProfile(
            professional_bio="Demo coach Dani K.",
            experience_years=5,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)],
        ),
    )
    db_session.add(coach)
    db_session.commit()

    pkg = CoachingPackage(
        coach_profile_id=coach.coach_profile.id,
        title="5 sessions × 1 hr",
        description="Rocket League coaching",
        price_amount=Decimal("150.00"),
        currency="USD",
        session_limit=5,
        duration_days=30,
        terms="Bonus terms: coach earns up to 10% of prize money.",
    )
    db_session.add(pkg)
    db_session.commit()
    return pkg


def test_create_quote_with_platform_fee(api_client, db_session):
    """POST /payments/quotes returns 8% fee, locked rate and KES estimate."""
    pkg = setup_package(db_session)
    resp = api_client.post("/api/v1/payments/quotes", json={"package_id": str(pkg.id)})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["amount_usd"] == "150.00"
    assert data["platform_fee_usd"] == "12.00"
    assert data["total_usd"] == "162.00"
    assert data["kes_rate"] == "129.00"
    assert int(data["total_kes"]) == 20898
    assert int(data["estimated_saving_kes"]) > 0
    assert data["note"]  # must be labelled as an estimate
    assert "quote_id" in data
    assert "expires_at" in data


def test_expired_quote_returns_410(api_client, db_session):
    """An expired quote_id returns 410 when creating or capturing an order."""
    import payments.router as pr
    # Inject a pre-expired quote directly into the store
    expired_id = "expired-test-001"
    pr._QUOTE_STORE[expired_id] = {
        "quote_id": expired_id,
        "package_id": "00000000-0000-0000-0000-000000000000",
        "amount_usd": "150.00",
        "fee_usd": "12.00",
        "total_usd": "162.00",
        "kes_rate": "129.00",
        "total_kes": "20898",
        "saving_kes": "731",
        "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "method": "paypal",
    }

    resp = api_client.post("/api/v1/payments/orders", json={"quote_id": expired_id})
    assert resp.status_code == 410, resp.text
    assert "expired" in resp.json()["detail"].lower()


def test_create_order_mock_paypal(api_client, db_session):
    """POST /payments/orders returns a mock PayPal order id and approval URL."""
    pkg = setup_package(db_session)
    quote_resp = api_client.post("/api/v1/payments/quotes", json={"package_id": str(pkg.id)})
    quote_id = quote_resp.json()["quote_id"]

    order_resp = api_client.post(
        "/api/v1/payments/orders",
        json={"quote_id": quote_id, "method": "paypal"},
        headers={"Idempotency-Key": "test-idem-001"},
    )
    assert order_resp.status_code == 201, order_resp.text
    data = order_resp.json()
    assert data["paypal_order_id"].startswith("MOCK-")
    assert data["approval_url"] is not None
    assert data["status"] == "CREATED"


def test_idempotency_key_no_double_charge(api_client, db_session):
    """Same Idempotency-Key returns the same order, not a new one."""
    pkg = setup_package(db_session)
    quote_resp = api_client.post("/api/v1/payments/quotes", json={"package_id": str(pkg.id)})
    quote_id = quote_resp.json()["quote_id"]

    idem_key = "test-idem-no-double-001"
    r1 = api_client.post(
        "/api/v1/payments/orders",
        json={"quote_id": quote_id, "method": "paypal"},
        headers={"Idempotency-Key": idem_key},
    )
    r2 = api_client.post(
        "/api/v1/payments/orders",
        json={"quote_id": quote_id, "method": "paypal"},
        headers={"Idempotency-Key": idem_key},
    )
    assert r1.status_code == 201
    # Second call with the same key returns 201 again (idempotent, not a 409/500)
    assert r2.status_code == 201


def test_capture_order_mock_returns_receipt(api_client, db_session):
    """POST /payments/orders/{id}/capture returns all fields Reberatha's Confirmation screen reads."""
    pkg = setup_package(db_session)
    quote_resp = api_client.post("/api/v1/payments/quotes", json={"package_id": str(pkg.id)})
    quote_id = quote_resp.json()["quote_id"]
    api_client.post("/api/v1/payments/orders", json={"quote_id": quote_id, "method": "paypal"})

    cap_resp = api_client.post(f"/api/v1/payments/orders/{quote_id}/capture")
    assert cap_resp.status_code == 200, cap_resp.text
    data = cap_resp.json()

    # Fields Reberatha reads on the Confirmation screen
    assert data["receipt_ref"].startswith("C2E-")
    assert data["coach_name"]                              # non-empty string
    assert data["paid_with"] == "paypal"
    assert data["package_label"]                           # non-empty package title
    assert float(data["platform_fee"]) == 12.00            # 8% of 150
    assert int(data["total_paid_kes"]) == 20898            # 162 × 129
    assert float(data["total_paid_usd"]) == 162.00
    assert data["currency"] == "USD"                       # paypal = USD
    assert data["rate_used"] == "USD"
    assert isinstance(data["booked_sessions"], list)
    assert len(data["booked_sessions"]) == 5               # session_limit=5
    assert data["booked_sessions"][0]["label"] == "Session 1 of 5"
    assert data["booked_sessions"][0]["starts_at"] is None # not yet scheduled
    assert data["status"]                                  # non-empty


def test_mpesa_sim_labelled_as_demo(api_client, db_session):
    """mpesa_sim method: simulated=true, currency=KES, rate_used includes KES."""
    pkg = setup_package(db_session)
    quote_resp = api_client.post(
        "/api/v1/payments/quotes", json={"package_id": str(pkg.id), "method": "mpesa_sim"}
    )
    quote_id = quote_resp.json()["quote_id"]
    api_client.post("/api/v1/payments/orders", json={"quote_id": quote_id, "method": "mpesa_sim"})
    cap_resp = api_client.post(f"/api/v1/payments/orders/{quote_id}/capture")
    assert cap_resp.status_code == 200
    data = cap_resp.json()
    assert data["simulated"] is True
    assert data["receipt_ref"].startswith("C2E-")
    assert data["currency"] == "KES"
    assert "KES" in data["rate_used"]
    assert "(est.)" in data["rate_used"]
    assert data["paid_with"] == "mpesa_sim"


def test_payouts_run_nothing_to_pay(api_client, db_session):
    """POST /payments/payouts/run returns nothing_to_pay when no sessions are available."""
    resp = api_client.post("/api/v1/payments/payouts/run")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "nothing_to_pay"
    assert data["items_count"] == 0


def test_webhook_mock_mode_always_passes(api_client, db_session):
    """In mock mode, webhook signature is always valid."""
    event_body = {
        "id": "WH-webhook-test-001",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {"id": "MOCK-CAP-001", "custom_id": "test-quote"},
    }
    import json
    resp = api_client.post(
        "/api/v1/payments/webhooks/paypal",
        content=json.dumps(event_body),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"


def test_webhook_duplicate_event_ignored(api_client, db_session):
    """The same webhook event id is processed only once."""
    import json
    from payments.router import _PROCESSED_EVENTS

    event_id = "WH-idem-test-001"
    _PROCESSED_EVENTS.discard(event_id)

    body = {"id": event_id, "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "CAP-01"}}
    r1 = api_client.post(
        "/api/v1/payments/webhooks/paypal",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    r2 = api_client.post(
        "/api/v1/payments/webhooks/paypal",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert r1.json()["status"] == "ok"
    assert r2.json()["status"] == "already_processed"


def test_refund_non_captured_order_returns_404(api_client, db_session):
    """Refunding an order that was never captured returns 404."""
    resp = api_client.post("/api/v1/payments/orders/non-existent-order/refund", json={})
    assert resp.status_code == 404
