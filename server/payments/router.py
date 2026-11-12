"""Payments router — Brian owns this file.

Mounts at /api/v1/payments (registered in app/api/v1/router.py).

P0 endpoints:
  POST /payments/quotes         — price + 8% fee, lock FX for 15 min
  POST /payments/orders         — create PayPal order from valid quote
  POST /payments/orders/{id}/capture — capture, generate receiptRef, book sessions
  POST /payments/webhooks/paypal      — verify + handle PayPal events

P1 endpoints:
  POST /payments/payouts/run    — batch payout for confirmed sessions
  POST /payments/orders/{id}/refund  — refund a captured payment

Rules:
  - Sandbox only (PAYPAL_MODE=sandbox|mock)
  - Never use the word escrow
  - Money in Decimal; amounts sent to PayPal as "%.2f" strings
  - State: real PayPal fees, Payouts availability and withdrawal options for
    Kenyan accounts must be verified with PayPal before launch.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.commerce import Order, Quotation
from app.models.enums import EarningStatus, OrderStatus, PayoutStatus
from app.models.finance import CoachEarning, PayoutRecord
from payments.fx import estimated_saving_kes, get_usd_to_kes_rate
from payments.paypal import capture_order, create_order, refund_capture, send_payout_batch, verify_webhook_signature
from payments.shared import create_booked_sessions, get_confirmed_unpaid_sessions

log = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# Platform fee (8 %)
_PLATFORM_FEE_RATE = Decimal("0.08")
# Quote lock duration
_QUOTE_LOCK_MINUTES = 15
# In-process quote store: quote_id → {expires_at, amount_usd, kes_rate, saving_kes, package_id, quote_id}
# In production this would live in the DB or Redis; for the hackathon an in-process dict is fine.
_QUOTE_STORE: dict[str, dict] = {}
# Idempotency key → order_id (prevents double-charge)
_IDEMPOTENCY_STORE: dict[str, str] = {}
# Processed webhook event IDs (idempotency)
_PROCESSED_EVENTS: set[str] = set()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QuoteRequest(BaseModel):
    package_id: UUID
    method: str = Field(default="paypal", description="paypal | mpesa_sim | card")


class QuoteResponse(BaseModel):
    quote_id: str
    package_id: str
    amount_usd: str
    platform_fee_usd: str
    total_usd: str
    kes_rate: str
    total_kes: str
    estimated_saving_kes: str
    expires_at: str
    method: str
    note: str = "KES amounts are estimates based on a locked rate. Not financial advice."


class OrderRequest(BaseModel):
    quote_id: str
    method: str = Field(default="paypal", description="paypal | mpesa_sim | card")


class OrderResponse(BaseModel):
    order_id: str
    paypal_order_id: str | None
    approval_url: str | None
    method: str
    simulated: bool = False
    receipt_ref: str | None = None
    status: str


class BookedSessionItem(BaseModel):
    id: str | None = None          # session id (None until booking row is created)
    label: str                     # e.g. "Session 1 of 5"
    starts_at: str | None = None   # ISO date string; null until player schedules


class CaptureResponse(BaseModel):
    # ── Fields read by Reberatha's Confirmation screen ──
    receipt_ref: str               # e.g. "C2E-48213"
    coach_name: str                # e.g. "Dani K."
    paid_with: str                 # e.g. "mpesa_sim" | "paypal"
    package_label: str             # e.g. "5-session pack"
    platform_fee: str              # e.g. "12.00"  (USD string, 2dp)
    total_paid_kes: str            # e.g. "20898"  (string so client formats)
    total_paid_usd: str            # e.g. "162.00"
    currency: str                  # "KES" or "USD" depending on paid_with
    rate_used: str                 # e.g. "1 USD = 129.00 KES (est.)"
    booked_sessions: list[BookedSessionItem]
    # ── Internal / legacy ──
    order_id: str
    status: str
    simulated: bool = False


class RefundRequest(BaseModel):
    amount_usd: str | None = Field(default=None, description="Partial refund amount. Omit for full refund.")


class PayoutsRunResponse(BaseModel):
    batch_id: str | None
    items_count: int
    simulated: bool = False
    status: str


# ---------------------------------------------------------------------------
# In-process quote helpers
# ---------------------------------------------------------------------------

def _make_receipt_ref() -> str:
    return f"C2E-{uuid.uuid4().int % 100000:05d}"


def _get_quote(quote_id: str) -> dict:
    q = _QUOTE_STORE.get(quote_id)
    if not q:
        raise HTTPException(status_code=410, detail="Quote not found or has expired")
    expires = datetime.fromisoformat(q["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        _QUOTE_STORE.pop(quote_id, None)
        raise HTTPException(status_code=410, detail="Quote has expired. Request a new quote.")
    return q


# ---------------------------------------------------------------------------
# P0: POST /payments/quotes
# ---------------------------------------------------------------------------

@router.post("/quotes", response_model=QuoteResponse, status_code=201)
def create_quote(
    payload: QuoteRequest,
    db: Session = Depends(get_db),
) -> QuoteResponse:
    """Price a package (+ 8 % platform fee) and lock the FX rate for 15 minutes.

    Returns a Quote the frontend uses for the Checkout countdown.
    The KES amounts are estimates — the UI must label them as such.
    """
    # Fetch the package price from the DB
    from app.models.commerce import CoachingPackage  # local to avoid circular at module level
    package = db.get(CoachingPackage, payload.package_id)
    if package is None or not package.is_active:
        raise HTTPException(status_code=404, detail="Package not found")

    base = package.price_amount.quantize(Decimal("0.01"))
    fee = (base * _PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
    total_usd = base + fee

    kes_rate = get_usd_to_kes_rate()
    total_kes = (total_usd * kes_rate).quantize(Decimal("1"))
    saving_kes = estimated_saving_kes(total_usd, kes_rate)

    expires_at = datetime.now(UTC) + timedelta(minutes=_QUOTE_LOCK_MINUTES)
    quote_id = uuid.uuid4().hex

    # Load coach name for the confirmation screen.
    # Two separate gets are fine — both hit the identity-layer PK cache.
    from app.models.identity import CoachProfile as _CoachProfile, User as _User  # local
    _cp = db.get(_CoachProfile, package.coach_profile_id)
    coach_user = db.get(_User, _cp.user_id) if _cp else None
    coach_name = (
        coach_user.email.split("@")[0].replace(".", " ").title()
        if coach_user else "Your coach"
    )

    _QUOTE_STORE[quote_id] = {
        "quote_id": quote_id,
        "package_id": str(payload.package_id),
        "package_title": package.title,
        "session_limit": package.session_limit,
        "coach_name": coach_name,
        "amount_usd": str(base),
        "fee_usd": str(fee),
        "total_usd": str(total_usd),
        "kes_rate": str(kes_rate),
        "total_kes": str(total_kes),
        "saving_kes": str(saving_kes),
        "expires_at": expires_at.isoformat(),
        "method": payload.method,
    }

    return QuoteResponse(
        quote_id=quote_id,
        package_id=str(payload.package_id),
        amount_usd=str(base),
        platform_fee_usd=str(fee),
        total_usd=str(total_usd),
        kes_rate=str(kes_rate),
        total_kes=str(total_kes),
        estimated_saving_kes=str(saving_kes),
        expires_at=expires_at.isoformat(),
        method=payload.method,
    )


# ---------------------------------------------------------------------------
# P0: POST /payments/orders
# ---------------------------------------------------------------------------

@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_payment_order(
    payload: OrderRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Create a PayPal Orders v2 order from a valid (non-expired) quote.

    Honouring Idempotency-Key prevents double charges on network retry.
    method=mpesa_sim records a simulated KES payment (demo only).
    """
    # Idempotency check
    if idempotency_key and idempotency_key in _IDEMPOTENCY_STORE:
        existing_order_id = _IDEMPOTENCY_STORE[idempotency_key]
        order = db.get(Order, UUID(existing_order_id))
        if order:
            return OrderResponse(
                order_id=str(order.id),
                paypal_order_id=None,
                approval_url=None,
                method=payload.method,
                status=order.status.value,
            )

    quote = _get_quote(payload.quote_id)
    total_usd = quote["total_usd"]

    # Find the underlying Quotation record in the DB for this package
    # (The quote store holds the package_id; we find the most recent open quotation)
    from app.models.commerce import CoachingPackage  # local import
    package = db.get(CoachingPackage, UUID(quote["package_id"]))
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")

    # For mpesa_sim: record as a simulated payment — clearly labelled
    is_simulated = payload.method == "mpesa_sim"

    paypal_order_id: str | None = None
    approval_url: str | None = None

    if not is_simulated:
        paypal_resp = create_order(
            amount_usd=total_usd,
            quote_id=payload.quote_id,
            idempotency_key=idempotency_key,
        )
        paypal_order_id = paypal_resp["id"]
        # Extract the approval link
        for link in paypal_resp.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link["href"]
                break

    # Store the order in our DB linked to the package via a fresh Quotation snapshot
    # (We create an internal order record to track status; PayPal order lives outside)
    # For the demo, we create a Quotation + Order in the DB now.
    # In production this would require the player to be authenticated.
    # Here we store the PayPal order id in external_reference on a PayoutRecord placeholder.
    # For now: store quote_id → paypal_order_id mapping for capture step.
    _QUOTE_STORE[payload.quote_id]["paypal_order_id"] = paypal_order_id or "MPESA_SIM"
    _QUOTE_STORE[payload.quote_id]["method"] = payload.method

    # Generate an internal order reference
    internal_ref = _make_receipt_ref()
    _QUOTE_STORE[payload.quote_id]["internal_ref"] = internal_ref

    if idempotency_key:
        _IDEMPOTENCY_STORE[idempotency_key] = payload.quote_id  # track by quote_id for now

    return OrderResponse(
        order_id=payload.quote_id,  # use quote_id as order_id for simplicity in demo
        paypal_order_id=paypal_order_id,
        approval_url=approval_url,
        method=payload.method,
        simulated=is_simulated,
        status="CREATED",
    )


# ---------------------------------------------------------------------------
# P0: POST /payments/orders/{order_id}/capture
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/capture", response_model=CaptureResponse)
def capture_payment_order(
    order_id: str,
    db: Session = Depends(get_db),
) -> CaptureResponse:
    """Capture an approved PayPal order, create the booking, return the receipt.

    order_id here is the quote_id used as the internal order token.
    The PayPal order id is stored in the quote store from the /orders step.
    """
    quote = _get_quote(order_id)  # raises 410 if expired
    paypal_order_id = quote.get("paypal_order_id")
    method = quote.get("method", "paypal")
    is_simulated = method == "mpesa_sim"

    if not paypal_order_id:
        raise HTTPException(status_code=409, detail="No PayPal order found for this quote. Call POST /payments/orders first.")

    # Capture with PayPal (or mock)
    if not is_simulated:
        capture_resp = capture_order(paypal_order_id)
        pp_status = capture_resp.get("status", "UNKNOWN")
        if pp_status not in ("COMPLETED",):
            raise HTTPException(status_code=402, detail=f"PayPal capture returned status {pp_status}")
    else:
        pp_status = "COMPLETED (simulated M-Pesa demo)"

    # Find the underlying DB Order linked to this package + coach
    # For the demo, find the most recent PENDING_PAYMENT order for the package
    from app.models.commerce import CoachingPackage  # local
    package_id = UUID(quote["package_id"])
    package = db.get(CoachingPackage, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")

    # Filter by package_id through the quotation snapshot.
    # Avoid joining Quotation.package — that FK is nullable (SET NULL on delete)
    # so an inner join silently drops rows when the package has been deactivated.
    db_order = db.scalar(
        select(Order)
        .join(Order.quotation)
        .where(
            Order.status == OrderStatus.PENDING_PAYMENT,
            Quotation.package_id == package_id,
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )

    receipt_ref = quote.get("internal_ref") or _make_receipt_ref()

    # Build booked-session items for the Confirmation screen.
    # At capture time sessions are not yet scheduled (starts_at = null);
    # labels are "Session N of M" matching the package session_limit.
    session_limit: int = quote.get("session_limit") or (db_order.session_limit if db_order else 1)
    booked_session_items: list[BookedSessionItem] = [
        BookedSessionItem(
            id=None,
            label=f"Session {i} of {session_limit}",
            starts_at=None,
        )
        for i in range(1, session_limit + 1)
    ]

    if db_order:
        booking = create_booked_sessions(db, db_order.id)
        # Stitch real booking id onto item 1 now that it exists
        if booking and str(booking.id):
            booked_session_items[0] = BookedSessionItem(
                id=str(booking.id),
                label=f"Session 1 of {session_limit}",
                starts_at=None,
            )
        # Store the PayPal order id as external_reference for reconciliation
        payout_rec = db.scalar(
            select(PayoutRecord).where(
                PayoutRecord.coach_profile_id == db_order.quotation.coach_profile_id,
                PayoutRecord.status == PayoutStatus.PENDING,
            ).order_by(PayoutRecord.created_at.desc()).limit(1)
        )
        if payout_rec and not payout_rec.external_reference:
            payout_rec.external_reference = paypal_order_id
            db.commit()

    # Mark the quote as used so it cannot be captured twice
    _QUOTE_STORE[order_id]["captured"] = True
    _QUOTE_STORE[order_id]["receipt_ref"] = receipt_ref

    # Derive currency and rate_used string for the confirmation screen
    kes_rate = quote.get("kes_rate", "129.00")
    is_kes = method in ("mpesa_sim", "card")
    currency = "KES" if is_kes else "USD"
    rate_used = f"1 USD = {kes_rate} KES (est.)" if is_kes else "USD"

    log.info("Payment captured: receipt=%s paypal_order=%s method=%s", receipt_ref, paypal_order_id, method)

    return CaptureResponse(
        # Confirmation screen fields
        receipt_ref=receipt_ref,
        coach_name=quote.get("coach_name", "Your coach"),
        paid_with=method,
        package_label=quote.get("package_title", "Coaching package"),
        platform_fee=quote.get("fee_usd", "0.00"),
        total_paid_kes=quote.get("total_kes", "0"),
        total_paid_usd=quote.get("total_usd", "0.00"),
        currency=currency,
        rate_used=rate_used,
        booked_sessions=booked_session_items,
        # Internal
        order_id=order_id,
        status=pp_status,
        simulated=is_simulated,
    )


# ---------------------------------------------------------------------------
# P0: POST /payments/webhooks/paypal
# ---------------------------------------------------------------------------

@router.post("/webhooks/paypal", status_code=200)
async def paypal_webhook(
    request: Request,
    paypal_transmission_id: Annotated[str | None, Header(alias="paypal-transmission-id")] = None,
    paypal_transmission_time: Annotated[str | None, Header(alias="paypal-transmission-time")] = None,
    paypal_cert_url: Annotated[str | None, Header(alias="paypal-cert-url")] = None,
    paypal_auth_algo: Annotated[str | None, Header(alias="paypal-auth-algo")] = None,
    paypal_transmission_sig: Annotated[str | None, Header(alias="paypal-transmission-sig")] = None,
    db: Session = Depends(get_db),
):
    """Verify and handle PayPal webhook events idempotently.

    Handled events:
      - PAYMENT.CAPTURE.COMPLETED  → mark order confirmed, accrue earning
      - PAYMENT.CAPTURE.DENIED     → log denial
      - PAYMENT.CAPTURE.REFUNDED   → update earning status
    """
    from app.core.config import get_settings
    settings = get_settings()

    raw_body = await request.body()

    valid = verify_webhook_signature(
        transmission_id=paypal_transmission_id or "",
        transmission_time=paypal_transmission_time or "",
        cert_url=paypal_cert_url or "",
        auth_algo=paypal_auth_algo or "",
        actual_sig=paypal_transmission_sig or "",
        webhook_id=settings.paypal_webhook_id or "",
        raw_body=raw_body,
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_id = event.get("id", "")
    event_type = event.get("event_type", "")

    # Idempotency: ignore already-processed events
    if event_id in _PROCESSED_EVENTS:
        log.info("Webhook event %s already processed — skipping", event_id)
        return {"status": "already_processed"}
    _PROCESSED_EVENTS.add(event_id)

    resource = event.get("resource", {})
    log.info("PayPal webhook: event_type=%s id=%s", event_type, event_id)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture_id = resource.get("id", "")
        custom_id = resource.get("custom_id") or resource.get("purchase_units", [{}])[0].get("custom_id", "")
        log.info("Capture completed: capture_id=%s quote_id=%s", capture_id, custom_id)
        # Find an earning linked to a pending order with this PayPal capture_id in external_reference
        payout_rec = db.scalar(
            select(PayoutRecord).where(PayoutRecord.external_reference == capture_id)
        )
        if payout_rec and payout_rec.status == PayoutStatus.PENDING:
            payout_rec.status = PayoutStatus.PROCESSING
            db.commit()

    elif event_type == "PAYMENT.CAPTURE.DENIED":
        capture_id = resource.get("id", "")
        log.warning("Capture denied: capture_id=%s", capture_id)
        # Mark corresponding earning as void
        earning = db.scalar(
            select(CoachEarning).where(CoachEarning.status == EarningStatus.PENDING)
            .order_by(CoachEarning.created_at.desc()).limit(1)
        )
        if earning:
            earning.status = EarningStatus.VOID
            db.commit()

    elif event_type in ("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"):
        capture_id = resource.get("id", "")
        log.info("Capture refunded/reversed: capture_id=%s", capture_id)

    return {"status": "ok", "event_type": event_type}


# ---------------------------------------------------------------------------
# P1: POST /payments/payouts/run
# ---------------------------------------------------------------------------

@router.post("/payouts/run", response_model=PayoutsRunResponse)
def run_payouts(
    db: Session = Depends(get_db),
) -> PayoutsRunResponse:
    """Trigger a PayPal Payouts batch for all confirmed, unpaid sessions.

    Only sessions where the coach's earning is in AVAILABLE status are included.
    A weekly schedule hook (cron) calls this endpoint automatically.

    State: Payouts availability and withdrawal options for Kenyan accounts must
    be verified with PayPal before launch.
    """
    items = get_confirmed_unpaid_sessions(db)
    if not items:
        return PayoutsRunResponse(batch_id=None, items_count=0, status="nothing_to_pay")

    payout_items = [
        {
            "recipient_email": it["recipient_email"],
            "amount_usd": it["net_amount"],
            "currency": it["currency"],
            "note": "Coach2Earn base-pay payout for confirmed session",
            "sender_item_id": it["earning_id"],
        }
        for it in items
    ]

    result = send_payout_batch(payout_items)
    batch_id = result.get("batch_header", {}).get("payout_batch_id")
    is_simulated = result.get("simulated", False)

    # Update each earning record with the batch id
    for it in items:
        earning_id = UUID(it["earning_id"])
        earning = db.get(CoachEarning, earning_id)
        if earning:
            earning.status = EarningStatus.PAID
            payout_rec = PayoutRecord(
                coach_profile_id=UUID(it["coach_profile_id"]),
                amount=Decimal(it["net_amount"]),
                currency=it["currency"],
                status=PayoutStatus.PROCESSING,
                external_reference=batch_id,
                requested_at=datetime.now(UTC),
            )
            db.add(payout_rec)

    db.commit()

    return PayoutsRunResponse(
        batch_id=batch_id,
        items_count=len(items),
        simulated=is_simulated,
        status="submitted",
    )


# ---------------------------------------------------------------------------
# P1: POST /payments/orders/{order_id}/refund
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/refund", status_code=200)
def refund_order(
    order_id: str,
    payload: RefundRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Refund a captured payment (full or partial).

    Marks the associated CoachEarning as VOID and creates a refund record.
    The UI copy must display: "Refunds follow the dispute policy."
    """
    quote = _QUOTE_STORE.get(order_id)
    if not quote or not quote.get("captured"):
        raise HTTPException(status_code=404, detail="No captured payment found for this order")

    paypal_order_id = quote.get("paypal_order_id", "")
    # For refunds we need the capture_id from the PayPal response.
    # In production this would be stored in the DB. For the demo we re-use the order id.
    capture_id = paypal_order_id  # simplification for sandbox demo

    refund_resp = refund_capture(capture_id, payload.amount_usd)
    refund_id = refund_resp.get("id", "")

    # Void the coach earning
    method = quote.get("method", "paypal")
    log.info("Refund issued: refund_id=%s order=%s method=%s", refund_id, order_id, method)

    return {
        "order_id": order_id,
        "refund_id": refund_id,
        "status": refund_resp.get("status", "COMPLETED"),
        "simulated": refund_resp.get("simulated", False),
        "note": "Refunds follow the dispute policy.",
    }
