"""Passport endpoints: Skills Passport and evidence management."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_player
from app.db.session import get_db
from app.models.identity import User

router = APIRouter(prefix="/players", tags=["passport"])

_ALLOWED_EVIDENCE_TYPES = {"ballchasing_replay", "video", "tournament"}

# In-memory evidence store for demo — replaced by DB persistence in full build
_demo_evidence: list[dict] = [
    {
        "id": "ev-001",
        "type": "ballchasing_replay",
        "url": "https://ballchasing.com/replay/demo-abc123",
        "addedAt": "2026-10-15T10:00:00Z",
    },
    {
        "id": "ev-002",
        "type": "tournament",
        "url": "https://start.gg/tournament/nairobi-rl-open",
        "addedAt": "2026-10-20T09:30:00Z",
    },
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReplayStats(BaseModel):
    matches: int
    goals: int
    saves: int
    shots: int
    boostPerMinute: float


class EvidenceItem(BaseModel):
    id: str
    type: str
    url: str
    addedAt: str


class FeedbackEntry(BaseModel):
    sessionId: str
    coachName: str
    date: str
    strengths: list[str]
    focusAreas: list[str]
    nextGoals: list[str]


class PlayerSummary(BaseModel):
    id: str
    name: str
    game: str


class PassportResponse(BaseModel):
    player: PlayerSummary
    rank: str
    replayStats: ReplayStats
    evidence: list[EvidenceItem]
    feedback: list[FeedbackEntry]


class AddEvidenceRequest(BaseModel):
    type: str  # "ballchasing_replay" | "video" | "tournament"
    url: str


# ---------------------------------------------------------------------------
# GET /players/{player_id}/passport
# ---------------------------------------------------------------------------


@router.get(
    "/{player_id}/passport",
    response_model=PassportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a player's Skills Passport: rank, replay stats, evidence and feedback",
)
def get_passport(
    player_id: UUID,
    db: Session = Depends(get_db),
) -> PassportResponse:
    """
    Returns the player's Skills Passport.
    Replay stats come from the Ballchasing API (or the cached sample when
    DEMO_MODE=true or BALLCHASING_API_KEY is absent).
    The passport is evidence — not a credential. It does not affect the
    Verified badge, which is controlled by a human reviewer only.
    """
    from .ballchasing import fetch_player_replays

    # Use a fixed demo steam ID — in production this comes from the player's profile
    demo_steam_id = "demo-steam-001"
    stats = fetch_player_replays(demo_steam_id)

    return PassportResponse(
        player=PlayerSummary(id=str(player_id), name="Demo Player", game="rocket_league"),
        rank="Diamond II",
        replayStats=ReplayStats(**stats),
        evidence=[EvidenceItem(**e) for e in _demo_evidence],
        feedback=[
            FeedbackEntry(
                sessionId="session-001",
                coachName="Dani K.",
                date="2026-11-12T14:00:00Z",
                strengths=["Strong aerial control", "Good boost awareness"],
                focusAreas=["Shadow defence positioning", "Rotation recovery after boost pad"],
                nextGoals=[
                    "Practice 50/50 challenges in freeplay",
                    "Review shadow defence replay clips",
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# POST /players/{player_id}/evidence
# ---------------------------------------------------------------------------


@router.post(
    "/{player_id}/evidence",
    response_model=list[EvidenceItem],
    status_code=status.HTTP_201_CREATED,
    summary="Add an evidence link to a player's passport",
)
def add_evidence(
    player_id: UUID,
    payload: AddEvidenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_player),
) -> list[EvidenceItem]:
    """
    Appends a new evidence link (replay, video, or tournament result) to the
    player's passport and returns the updated evidence list.
    """
    if payload.type not in _ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"type must be one of: {', '.join(sorted(_ALLOWED_EVIDENCE_TYPES))}",
        )
    new_item = {
        "id": f"ev-{len(_demo_evidence) + 1:03d}",
        "type": payload.type,
        "url": payload.url,
        "addedAt": datetime.now(timezone.utc).isoformat(),
    }
    _demo_evidence.append(new_item)
    # TODO: persist to DB instead of in-memory list
    return [EvidenceItem(**e) for e in _demo_evidence]
