"""Ballchasing API client with local file cache.

Free tier: 16 requests/hour — always check cache first.
Cache file: server/passport/cache/ballchasing_sample.json

Environment variables:
    BALLCHASING_API_KEY  — free from ballchasing.com
    DEMO_MODE            — set "true" to always use cache (no live calls)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_BALLCHASING_BASE = "https://ballchasing.com/api"
_CACHE_FILE = Path(__file__).parent / "cache" / "ballchasing_sample.json"
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _is_demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")


def _api_key() -> str | None:
    return os.environ.get("BALLCHASING_API_KEY") or None


def _cache_is_fresh() -> bool:
    if not _CACHE_FILE.exists():
        return False
    mtime = _CACHE_FILE.stat().st_mtime
    age = datetime.now(timezone.utc).timestamp() - mtime
    return age < _CACHE_TTL_SECONDS


def _load_cache() -> dict:
    with _CACHE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _write_cache(data: dict) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)


def _compute_stats(replays: list[dict], player_steam_id: str) -> dict:
    """Aggregate per-player stats across a list of replay objects."""
    matches = len(replays)
    goals = saves = shots = total_boost = total_duration_secs = 0

    for replay in replays:
        duration = replay.get("duration", 300)  # default 5 min if absent
        total_duration_secs += duration
        for player in replay.get("players", []):
            pid = player.get("id", {}).get("id", "")
            if pid != player_steam_id:
                continue
            core = player.get("stats", {}).get("core", {})
            boost = player.get("stats", {}).get("boost", {})
            goals += core.get("goals", 0)
            saves += core.get("saves", 0)
            shots += core.get("shots", 0)
            total_boost += boost.get("amount_collected", 0)

    minutes = total_duration_secs / 60 if total_duration_secs else 1
    boost_per_minute = round(total_boost / minutes, 1) if total_boost else 0.0

    return {
        "matches": matches,
        "goals": goals,
        "saves": saves,
        "shots": shots,
        "boostPerMinute": boost_per_minute,
    }


def fetch_player_replays(player_steam_id: str) -> dict:
    """
    Fetch and aggregate replay stats for a player.

    Returns a replayStats dict:
        { matches, goals, saves, shots, boostPerMinute }

    Falls back to cached sample when:
    - DEMO_MODE=true
    - BALLCHASING_API_KEY is not set
    - the live API call fails
    - cache is fresh (< 1 hour old)
    """
    # Always use cache in demo mode or when key is absent
    if _is_demo_mode() or not _api_key():
        logger.debug("Using cached Ballchasing sample (demo mode or no API key)")
        data = _load_cache()
        return _compute_stats(data.get("list", []), player_steam_id)

    # Use cache if fresh
    if _cache_is_fresh():
        logger.debug("Using fresh Ballchasing cache")
        data = _load_cache()
        return _compute_stats(data.get("list", []), player_steam_id)

    # Live API call
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{_BALLCHASING_BASE}/replays",
                params={"player-id": player_steam_id, "count": 20},
                headers={
                    "Authorization": _api_key(),
                    "User-Agent": "coach2earn/1.0",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            _write_cache(data)
            logger.info("Ballchasing live fetch OK for player %s", player_steam_id)
            return _compute_stats(data.get("list", []), player_steam_id)
    except Exception as exc:
        logger.warning("Ballchasing API call failed (%s), falling back to cache", exc)
        data = _load_cache()
        return _compute_stats(data.get("list", []), player_steam_id)
