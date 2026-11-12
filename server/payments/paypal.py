"""PayPal API client — wraps Orders v2 and Payouts v1.

Uses PAYPAL_MODE env var:
  - "sandbox"  → real PayPal Sandbox REST calls
  - "mock"     → deterministic fake responses (never hits the network)

Never commit credentials. Set via environment variables only.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
_LIVE_BASE = "https://api-m.paypal.com"

# ---------------------------------------------------------------------------
# Token cache (in-process; one process per Render worker is fine)
# ---------------------------------------------------------------------------
_token_cache: dict[str, Any] = {}


def _base_url() -> str:
    settings = get_settings()
    return _SANDBOX_BASE if settings.paypal_mode != "live" else _LIVE_BASE


def _get_access_token() -> str:
    """Return a cached OAuth 2 client-credentials token, refreshing when needed."""
    settings = get_settings()
    if settings.paypal_mode == "mock":
        return "mock-token"

    now = time.time()
    cached = _token_cache.get("token")
    if cached and _token_cache.get("expires_at", 0) > now + 30:
        return cached  # type: ignore[return-value]

    resp = httpx.post(
        f"{_base_url()}/v1/oauth2/token",
        auth=(
            settings.paypal_client_id or "",
            settings.paypal_client_secret.get_secret_value() if settings.paypal_client_secret else "",
        ),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return data["access_token"]


def _headers(idempotency_key: str | None = None) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        h["PayPal-Request-Id"] = idempotency_key
    return h


# ---------------------------------------------------------------------------
# Orders v2
# ---------------------------------------------------------------------------

def create_order(
    amount_usd: str,
    quote_id: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create a PayPal Orders v2 order. Returns the raw PayPal response dict."""
    settings = get_settings()
    if settings.paypal_mode == "mock":
        fake_id = f"MOCK-{uuid.uuid4().hex[:16].upper()}"
        return {
            "id": fake_id,
            "status": "CREATED",
            "simulated": True,
            "links": [
                {"rel": "approve", "href": f"https://sandbox.paypal.com/checkoutnow?token={fake_id}"},
                {"rel": "capture", "href": f"{_SANDBOX_BASE}/v2/checkout/orders/{fake_id}/capture"},
            ],
        }

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": "USD", "value": amount_usd},
                "custom_id": quote_id,
                "description": "Coach2Earn coaching package",
            }
        ],
    }
    resp = httpx.post(
        f"{_base_url()}/v2/checkout/orders",
        headers=_headers(idempotency_key),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def capture_order(paypal_order_id: str) -> dict[str, Any]:
    """Capture a previously approved PayPal order."""
    settings = get_settings()
    if settings.paypal_mode == "mock":
        return {
            "id": paypal_order_id,
            "status": "COMPLETED",
            "simulated": True,
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": f"MOCK-CAP-{uuid.uuid4().hex[:12].upper()}",
                                "status": "COMPLETED",
                                "amount": {"currency_code": "USD", "value": "0.00"},
                            }
                        ]
                    }
                }
            ],
        }

    resp = httpx.post(
        f"{_base_url()}/v2/checkout/orders/{paypal_order_id}/capture",
        headers=_headers(),
        json={},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refund_capture(capture_id: str, amount_usd: str | None = None) -> dict[str, Any]:
    """Refund a captured payment. Pass amount_usd for a partial refund."""
    settings = get_settings()
    if settings.paypal_mode == "mock":
        return {"id": f"MOCK-REFUND-{uuid.uuid4().hex[:12].upper()}", "status": "COMPLETED", "simulated": True}

    payload: dict[str, Any] = {}
    if amount_usd:
        payload["amount"] = {"currency_code": "USD", "value": amount_usd}

    resp = httpx.post(
        f"{_base_url()}/v2/payments/captures/{capture_id}/refund",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Payouts v1
# ---------------------------------------------------------------------------

def send_payout_batch(items: list[dict[str, Any]], email_subject: str = "Coach2Earn payout") -> dict[str, Any]:
    """Submit a PayPal Payouts batch.

    items is a list of dicts with keys:
      recipient_email, amount_usd (str), currency, note, sender_item_id
    """
    settings = get_settings()
    if settings.paypal_mode == "mock":
        batch_id = f"MOCK-BATCH-{uuid.uuid4().hex[:12].upper()}"
        return {
            "batch_header": {"payout_batch_id": batch_id, "batch_status": "PENDING"},
            "simulated": True,
        }

    payout_items = [
        {
            "recipient_type": "EMAIL",
            "amount": {"value": it["amount_usd"], "currency": it.get("currency", "USD")},
            "receiver": it["recipient_email"],
            "note": it.get("note", "Coach2Earn base-pay payout"),
            "sender_item_id": it["sender_item_id"],
        }
        for it in items
    ]

    payload = {
        "sender_batch_header": {
            "sender_batch_id": uuid.uuid4().hex,
            "email_subject": email_subject,
            "email_message": "Your Coach2Earn payout has been sent.",
        },
        "items": payout_items,
    }

    resp = httpx.post(
        f"{_base_url()}/v1/payments/payouts",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(
    transmission_id: str,
    transmission_time: str,
    cert_url: str,
    auth_algo: str,
    actual_sig: str,
    webhook_id: str,
    raw_body: bytes,
) -> bool:
    """Verify a PayPal webhook using the REST API verification endpoint.

    Falls back to True in mock mode so tests run without network.
    """
    settings = get_settings()
    if settings.paypal_mode == "mock":
        log.debug("paypal mock mode — webhook signature verification skipped")
        return True

    payload = {
        "transmission_id": transmission_id,
        "transmission_time": transmission_time,
        "cert_url": cert_url,
        "auth_algo": auth_algo,
        "actual_sig": actual_sig,
        "webhook_id": webhook_id,
        "webhook_event": json.loads(raw_body),
    }
    try:
        resp = httpx.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("verification_status") == "SUCCESS"
    except Exception:
        log.exception("PayPal webhook verification failed")
        return False
