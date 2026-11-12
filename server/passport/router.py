"""Passport endpoints: Skills Passport and evidence management."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_player
from app.db.session import get_db
from app.models.commerce import Booking, CoachingSession, Order, Quotation
from app.models.engagement import PlayerEvidence
from app.models.enums import SessionStatus
from app.models.identity import CoachProfile, PlayerProfile, User
from app.services.profiles import display_name_from_email

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

    user = db.get(User, player_id)
    if user is None:
        # Unknown player id — keep the original demo passport.
        return PassportResponse(
            player=PlayerSummary(id=str(player_id), name="Demo Player", game="rocket_league"),
            rank="Diamond II",
            replayStats=ReplayStats(**stats),
            evidence=[EvidenceItem(**e) for e in _demo_evidence],
            feedback=[_DEMO_FEEDBACK],
        )

    profile = user.player_profile
    game = "rocket_league"
    if profile is not None and profile.games:
        game = profile.games[0].specialisation.slug.replace("-", "_")
    return PassportResponse(
        player=PlayerSummary(id=str(user.id), name=display_name_from_email(user.email), game=game),
        rank=(profile.skill_level if profile and profile.skill_level else "Unranked"),
        replayStats=ReplayStats(**stats),
        evidence=_evidence_for(db, user.id),
        feedback=_feedback_for(db, profile),
    )


_DEMO_FEEDBACK = FeedbackEntry(
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


def _evidence_for(db: Session, user_id: UUID) -> list[EvidenceItem]:
    rows = db.scalars(
        select(PlayerEvidence).where(PlayerEvidence.user_id == user_id).order_by(PlayerEvidence.created_at)
    ).all()
    return [
        EvidenceItem(
            id=str(r.id),
            type=r.evidence_type,
            url=r.url,
            addedAt=(r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)).isoformat(),
        )
        for r in rows
    ]


def _feedback_for(db: Session, profile: PlayerProfile | None) -> list[FeedbackEntry]:
    """Structured feedback from the coach notes on this player's completed sessions."""
    if profile is None:
        return []
    from ai.router import _fallback_feedback  # deterministic parser, no LLM call

    sessions = db.scalars(
        select(CoachingSession)
        .join(CoachingSession.booking)
        .join(Booking.order)
        .join(Order.quotation)
        .options(selectinload(CoachingSession.booking).selectinload(Booking.order)
                 .selectinload(Order.quotation).selectinload(Quotation.coach_profile)
                 .selectinload(CoachProfile.user))
        .where(
            Quotation.player_profile_id == profile.id,
            CoachingSession.status == SessionStatus.COMPLETED,
            CoachingSession.coach_notes.is_not(None),
        )
        .order_by(CoachingSession.starts_at.desc())
        .limit(10)
    ).all()
    entries = []
    for s in sessions:
        parsed = _fallback_feedback(s.coach_notes or "")
        entries.append(FeedbackEntry(
            sessionId=str(s.id),
            coachName=display_name_from_email(s.booking.order.quotation.coach_profile.user.email),
            date=(s.starts_at if s.starts_at.tzinfo else s.starts_at.replace(tzinfo=timezone.utc)).isoformat(),
            strengths=parsed["strengths"],
            focusAreas=parsed["focusAreas"],
            nextGoals=parsed["nextGoals"],
        ))
    return entries


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
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="url must start with http:// or https://")
    if player_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only add evidence to your own passport")
    db.add(PlayerEvidence(user_id=current_user.id, evidence_type=payload.type, url=payload.url))
    db.commit()
    return _evidence_for(db, current_user.id)
