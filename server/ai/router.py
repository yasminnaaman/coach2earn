"""AI endpoints: coach matching, session feedback, verification evidence organiser.

Mount point (Hope wires this in server/app/main.py or equivalent):
    from server.ai.router import router as ai_router
    app.include_router(ai_router, prefix="/api/v1")

Endpoints:
    POST /ai/match
    POST /ai/sessions/{session_id}/feedback
    POST /ai/verification/submissions
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_coach
from app.db.session import get_db
from app.models.identity import User

router = APIRouter(prefix="/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MatchRequest(BaseModel):
    game: str
    role: str
    goal: str
    budgetUsd: float


class MatchedCoach(BaseModel):
    coachId: str
    name: str
    verified: bool
    endorsementCount: int
    priceUsd: float
    game: str
    role: str
    score: int
    reason: str
    reasonSource: str  # "ai" | "rule"
    bestMatch: bool


class FeedbackRequest(BaseModel):
    notes: str


class FeedbackResponse(BaseModel):
    strengths: list[str]
    focusAreas: list[str]
    nextGoals: list[str]


class EvidenceLink(BaseModel):
    type: str
    url: str
    description: str


class VerificationRequest(BaseModel):
    coachId: str
    links: list[EvidenceLink]


class VerificationResponse(BaseModel):
    claims: list[str]
    sources: list[dict]
    gaps: list[str]
    redFlags: list[str]
    summary: str


# ---------------------------------------------------------------------------
# POST /ai/match
# ---------------------------------------------------------------------------


@router.post(
    "/match",
    response_model=list[MatchedCoach],
    status_code=status.HTTP_200_OK,
    summary="Find and rank coaches by game, role, goal and budget",
)
def match_coaches(
    payload: MatchRequest,
    db: Session = Depends(get_db),
) -> list[MatchedCoach]:
    """
    Scores coaches against the query using a transparent scoring function,
    then calls the Groq LLM to write a one-line reason for each top result.
    Falls back to a deterministic reason if the LLM is unavailable.
    See README for the full scoring table.
    """
    # TODO: replace with scoring.score_coaches(db, payload) + llm.generate_reason()
    return [
        MatchedCoach(
            coachId="coach-001",
            name="Dani K.",
            verified=True,
            endorsementCount=6,
            priceUsd=30.0,
            game="rocket_league",
            role="forward",
            score=92,
            reason="Verified Rocket League coach with 6 community endorsements, within your budget.",
            reasonSource="rule",
            bestMatch=True,
        ),
        MatchedCoach(
            coachId="coach-002",
            name="Alex M.",
            verified=False,
            endorsementCount=2,
            priceUsd=25.0,
            game="rocket_league",
            role="forward",
            score=54,
            reason="Rocket League forward coach within budget, not yet verified.",
            reasonSource="rule",
            bestMatch=False,
        ),
    ]


# ---------------------------------------------------------------------------
# POST /ai/sessions/{session_id}/feedback
# ---------------------------------------------------------------------------


@router.post(
    "/sessions/{session_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Structure coach notes into strengths, focus areas and next goals",
)
def session_feedback(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach),
) -> FeedbackResponse:
    """
    Reads coach_notes from the CoachingSession record, passes them to the
    Groq LLM to extract structured feedback. Falls back to text parsing if
    the LLM is unavailable.
    AI organises what the coach wrote — it does not evaluate the player.
    """
    # TODO: replace with feedback.structure_feedback(session_id, db)
    return FeedbackResponse(
        strengths=["Strong aerial control", "Improving boost management"],
        focusAreas=["Shadow defence positioning"],
        nextGoals=[
            "Practice 50/50 challenges in freeplay",
            "Review shadow defence replay clips",
        ],
    )


# ---------------------------------------------------------------------------
# POST /ai/verification/submissions
# ---------------------------------------------------------------------------


@router.post(
    "/verification/submissions",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Organise coach evidence links into a structured summary for a human reviewer",
)
def verification_submission(
    payload: VerificationRequest,
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """
    Passes the coach's submitted evidence links to the Groq LLM, which extracts
    claims, identifies sources, notes gaps, and flags anything suspicious.
    The result is a summary for a HUMAN reviewer to act on.
    The AI NEVER marks anyone Verified. A person reviews every coach.
    """
    # TODO: replace with verification.organise_evidence(payload.coachId, payload.links)
    return VerificationResponse(
        claims=["Ex-national squad, Rocket League", "6 community endorsements"],
        sources=[link.model_dump() for link in payload.links],
        gaps=[],
        redFlags=[],
        summary=(
            "Coach Dani K. has submitted verifiable evidence of national-level play "
            "and community endorsements. No gaps or red flags identified. "
            "Ready for human review."
        ),
    )
