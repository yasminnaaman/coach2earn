"""FX rate provider — returns a USD→KES rate for quoting.

FX_PROVIDER env var controls the source:
  "fixed"   → always return FX_FIXED_RATE (default 129.00 for demo)
  "open"    → fetch from open.er-api.com (no key required, rate-limited)

All rates returned are estimates and must be labelled as such in the UI.
"""

from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

# Demo / fallback rate matching the build pack
_DEMO_RATE = Decimal("129.00")


def get_usd_to_kes_rate() -> Decimal:
    """Return the current USD → KES exchange rate.

    Always falls back to the fixed demo rate if the provider is unavailable.
    Callers must label the returned rate as an estimate.
    """
    settings = get_settings()
    provider = getattr(settings, "fx_provider", "fixed")
    fixed_rate = getattr(settings, "fx_fixed_rate", _DEMO_RATE)

    if provider == "fixed":
        return Decimal(str(fixed_rate))

    # open.er-api.com — free, no key
    try:
        resp = httpx.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5,
        )
        resp.raise_for_status()
        rate = resp.json()["rates"].get("KES")
        if rate:
            return Decimal(str(rate)).quantize(Decimal("0.01"))
    except Exception:
        log.warning("FX provider %s failed — falling back to fixed rate", provider)

    return Decimal(str(fixed_rate))


def estimated_saving_kes(amount_usd: Decimal, locked_rate: Decimal) -> Decimal:
    """Estimate the KES saving vs a typical direct PayPal conversion.

    Method: typical PayPal retail FX markup is ~3–4 % above the mid-market
    rate. We use 3.5 % as the estimate here. This is NOT a real fee —
    callers must label it as an estimate.

    estimated_saving = amount_usd × locked_rate × 0.035
    """
    markup = Decimal("0.035")
    saving = (amount_usd * locked_rate * markup).quantize(Decimal("1"))
    return saving
