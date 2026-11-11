"""Groq LLM client for one-line match reasons and structured text tasks.

Uses the OpenAI-compatible Groq API endpoint.
On any failure (missing key, timeout, API error) the caller receives None
and must use the deterministic fallback from scoring.py.

Environment variable:
    GROQ_API_KEY  — free key from console.groq.com
"""

from __future__ import annotations

import os
import logging

import httpx

logger = logging.getLogger(__name__)

_GROQ_BASE = "https://api.groq.com/openai/v1"
_MODEL = "llama-3.1-8b-instant"
_TIMEOUT = 8.0  # seconds — fast enough to not stall the request


def _api_key() -> str | None:
    return os.environ.get("GROQ_API_KEY") or None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def chat(system: str, user: str) -> str | None:
    """
    Send a single-turn chat completion to Groq.
    Returns the response text, or None on any failure.
    """
    key = _api_key()
    if not key:
        logger.debug("GROQ_API_KEY not set — skipping LLM call")
        return None

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 120,
        "temperature": 0.4,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_GROQ_BASE}/chat/completions",
                headers=_headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq LLM call failed: %s", exc)
        return None


def generate_reason(coach: dict, query: dict) -> str | None:
    """
    Ask the LLM to write a one-line match reason for this coach.
    Returns the reason string, or None so the caller can use fallback_reason().
    """
    system = (
        "You write one short sentence (max 20 words) explaining why a coach "
        "is a good match for a player's goal. Be specific and concrete. "
        "Do not use the word 'perfect'. Do not make certification claims."
    )
    user = (
        f"Coach: {coach.get('name')}, "
        f"game: {coach.get('game', '').replace('_', ' ')}, "
        f"role: {coach.get('role', '').replace('_', ' ')}, "
        f"verified: {coach.get('verified')}, "
        f"endorsements: {coach.get('endorsementCount')}, "
        f"price: ${coach.get('priceUsd')}/session.\n"
        f"Player goal: {query.get('goal', '')}."
    )
    return chat(system, user)


def structure_notes(notes: str) -> dict | None:
    """
    Ask the LLM to extract strengths, focus areas, and next goals from
    a coach's session notes. Returns a dict or None on failure.
    """
    system = (
        "You are a coaching assistant. Extract structured feedback from a coach's "
        "session notes. Return a JSON object with exactly three keys: "
        "'strengths' (list of strings), 'focusAreas' (list of strings), "
        "'nextGoals' (list of strings). Each item is one short phrase. "
        "Return only valid JSON, no extra text."
    )
    user = f"Session notes:\n{notes}"

    raw = chat(system, user)
    if raw is None:
        return None

    import json
    try:
        parsed = json.loads(raw)
        # Validate shape
        if all(k in parsed for k in ("strengths", "focusAreas", "nextGoals")):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        logger.warning("LLM returned invalid JSON for structure_notes")
        return None


def organise_evidence(coach_id: str, links: list[dict]) -> dict | None:
    """
    Ask the LLM to organise submitted evidence links into a structured summary
    for a human reviewer. Returns a dict or None on failure.
    The AI never marks anyone Verified.
    """
    system = (
        "You are a verification assistant. A human reviewer will read your output "
        "and make the final decision. Never say a coach is verified or approved. "
        "From the submitted evidence links, extract: "
        "'claims' (list: what each link claims to prove), "
        "'sources' (list of the links as-is), "
        "'gaps' (list: what evidence is missing), "
        "'redFlags' (list: anything suspicious). "
        "Also write a 'summary' of 2-3 sentences for the reviewer. "
        "Return only valid JSON with those five keys."
    )
    links_text = "\n".join(
        f"- [{l.get('type')}] {l.get('url')}: {l.get('description', '')}"
        for l in links
    )
    user = f"Coach ID: {coach_id}\nSubmitted evidence:\n{links_text}"

    raw = chat(system, user)
    if raw is None:
        return None

    import json
    try:
        parsed = json.loads(raw)
        if all(k in parsed for k in ("claims", "sources", "gaps", "redFlags", "summary")):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        logger.warning("LLM returned invalid JSON for organise_evidence")
        return None
