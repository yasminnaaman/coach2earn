"""Transparent coach scoring function.

Scoring table (documented in README.md):

  Component            Max pts  Rule
  -------------------  -------  ------------------------------------------------
  Game match           required  Eliminate coach if game slug does not match
  Role match           required  Eliminate coach if role slug does not match
  Verified             +20       verification_status == "approved"
  Endorsement count    0–20      min(count, 10) * 2
  Price within budget  +20       cheapest active package price_amount <= budgetUsd
  Availability         +20       availability dict is non-empty
  Endorsement spread   0–20      min(distinct_communities, 10) * 2
  -------------------  -------  ------------------------------------------------
  Total                100
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def score_coach(coach: dict[str, Any], query: dict[str, Any]) -> int | None:
    """
    Score a single coach dict against a match query.

    Returns an integer 0-100, or None if the coach is eliminated
    (game or role does not match the query).

    Args:
        coach: dict with keys:
            game (str)              — slug, e.g. "rocket_league"
            role (str)              — slug, e.g. "forward"
            verified (bool)         — True when verification_status == "approved"
            endorsementCount (int)  — total endorsements
            endorsementCommunities (int) — distinct communities that endorsed
            priceUsd (float)        — cheapest active package price in USD
            hasAvailability (bool)  — True when availability dict is non-empty
        query: dict with keys:
            game (str)
            role (str)
            budgetUsd (float)
    """
    # --- Hard filters (elimination) ---
    if coach.get("game", "").lower() != query.get("game", "").lower():
        return None
    if coach.get("role", "").lower() != query.get("role", "").lower():
        return None

    score = 0

    # +20: verified (human-approved only)
    if coach.get("verified", False):
        score += 20

    # 0-20: endorsement count (capped at 10 endorsements for full score)
    endorsement_count = int(coach.get("endorsementCount", 0))
    score += min(endorsement_count, 10) * 2

    # +20: price within budget
    price = float(coach.get("priceUsd", 0))
    budget = float(query.get("budgetUsd", 0))
    if price <= budget:
        score += 20

    # +20: has open availability slots
    if coach.get("hasAvailability", False):
        score += 20

    # 0-20: endorsement spread across distinct communities (capped at 10)
    communities = int(coach.get("endorsementCommunities", 0))
    score += min(communities, 10) * 2

    return score


def fallback_reason(coach: dict[str, Any], query: dict[str, Any]) -> str:
    """Build a deterministic one-line reason string from coach fields."""
    parts: list[str] = []

    if coach.get("verified"):
        parts.append("Verified")

    game = coach.get("game", "").replace("_", " ").title()
    role = coach.get("role", "").replace("_", " ").title()
    if game and role:
        parts.append(f"{game} {role} coach")

    count = int(coach.get("endorsementCount", 0))
    if count:
        parts.append(f"{count} community endorsement{'s' if count != 1 else ''}")

    budget = float(query.get("budgetUsd", 0))
    price = float(coach.get("priceUsd", 0))
    if price <= budget:
        parts.append(f"within your ${int(budget)} budget")

    return ", ".join(parts) + "." if parts else "Matches your search criteria."
