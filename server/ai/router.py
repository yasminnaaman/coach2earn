"""AI endpoints: coach matching, session feedback, verification evidence organiser."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_coach
from app.db.session import get_db
from app.models.commerce import CoachingPackage, CoachingSession
from app.models.enums import VerificationStatus
from app.models.identity import CoachProfile, CoachSpecialisation, Specialisation, User
from app.services.profiles import display_name_from_email

from .llm import generate_reason, organise_evidence, structure_notes
from .scoring import fallback_reason, score_coach

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
# Helpers
# ---------------------------------------------------------------------------


def _fallback_feedback(notes: str) -> dict:
    """
    Parse coach notes into structured feedback without the LLM.
    Lines starting with '+' -> strengths
    Lines starting with '-' -> focusAreas
    Lines starting with '>' -> nextGoals
    Unmarked lines        -> focusAreas
    """
    strengths, focus, goals = [], [], []
    for line in notes.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("+"):
            strengths.append(stripped[1:].strip())
        elif stripped.startswith(">"):
            goals.append(stripped[1:].strip())
        else:
            # lines starting with '-' or anything else -> focusAreas
            text = stripped.lstrip("-").strip()
            if text:
                focus.append(text)
    if not strengths and not focus and not goals:
        focus = [notes.strip()]
    return {"strengths": strengths, "focusAreas": focus, "nextGoals": goals}


def _fallback_verification(coach_id: str, links: list[dict]) -> dict:
    return {
        "claims": [l.get("url", "") for l in links],
        "sources": links,
        "gaps": ["Manual review required"],
        "redFlags": [],
        "summary": "Evidence submitted. Manual review required.",
    }


def _build_coach_dict(
    profile: CoachProfile,
    name: str,
    game_slug: str,
    role_slug: str,
    endorsement_count: int,
    endorsement_communities: int,
    cheapest_price_usd: float,
) -> dict:
    return {
        "coachId": str(profile.id),
        "name": name,
        "verified": profile.verification_status == VerificationStatus.APPROVED,
        "endorsementCount": endorsement_count,
        "endorsementCommunities": endorsement_communities,
        "priceUsd": cheapest_price_usd,
        "game": game_slug,
        "role": role_slug,
        "hasAvailability": bool(profile.availability),
    }


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
    Scores all coaches against the query using a transparent scoring function
    (see README for the full table), then calls the Groq LLM for a one-line
    reason on the top results. Falls back to a rule-based reason if the LLM
    is unavailable — the endpoint never fails because AI is down.
    """
    # Load all coach profiles with their specialisations and cheapest package
    profiles = db.scalars(select(CoachProfile)).all()

    scored: list[tuple[int, dict]] = []

    for profile in profiles:
        # Collect game/role slugs from specialisations
        for spec_link in profile.specialisations:
            spec: Specialisation = spec_link.specialisation
            if spec.category.value != "game":
                continue
            # Catalog slugs use hyphens ("rocket-league"); the frontend sends
            # underscores ("rocket_league"). Normalise so they compare equal.
            game_slug = spec.slug.replace("-", "_")
            # Roles are not in the schema yet, so a coach cannot be ruled out
            # by role — treat the requested role as matching.
            # NOTE: when Hope adds a role field to Specialisation, update this
            role_slug = payload.role

            # Cheapest active per-session price in USD (budget is per session)
            usd_packages = [
                float(p.price_amount) / p.session_limit
                for p in profile.packages
                if p.is_active and p.currency == "USD" and p.session_limit
            ]
            if not usd_packages:
                # No USD package — fall back to the cheapest in any currency
                usd_packages = [
                    float(p.price_amount) / p.session_limit
                    for p in profile.packages
                    if p.is_active and p.session_limit
                ]
            cheapest = round(min(usd_packages), 2) if usd_packages else 0.0

            # Endorsement count — Hope's model doesn't have an endorsements table yet
            # Using qualifications count as a proxy until endorsements are added
            endorsement_count = len(profile.qualifications)
            endorsement_communities = endorsement_count  # proxy

            coach_dict = _build_coach_dict(
                profile=profile,
                name=display_name_from_email(profile.user.email),  # until a name field exists
                game_slug=game_slug,
                role_slug=role_slug,
                endorsement_count=endorsement_count,
                endorsement_communities=endorsement_communities,
                cheapest_price_usd=cheapest,
            )

            s = score_coach(coach_dict, payload.model_dump())
            if s is not None:
                scored.append((s, coach_dict))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:10]

    results: list[MatchedCoach] = []
    for i, (s, coach_dict) in enumerate(top):
        # Call LLM for top 5; use rule-based for the rest
        ai_reason = generate_reason(coach_dict, payload.model_dump()) if i < 5 else None
        if ai_reason:
            reason, source = ai_reason, "ai"
        else:
            reason, source = fallback_reason(coach_dict, payload.model_dump()), "rule"

        results.append(
            MatchedCoach(
                coachId=coach_dict["coachId"],
                name=coach_dict["name"],
                verified=coach_dict["verified"],
                endorsementCount=coach_dict["endorsementCount"],
                priceUsd=coach_dict["priceUsd"],
                game=coach_dict["game"],
                role=coach_dict["role"],
                score=s,
                reason=reason,
                reasonSource=source,
                bestMatch=(i == 0),
            )
        )

    return results


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
    the LLM is unavailable. The AI organises what the coach wrote — it does
    not independently evaluate the player.
    """
    session = db.scalar(select(CoachingSession).where(CoachingSession.id == session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    notes = session.coach_notes or ""
    if not notes.strip():
        raise HTTPException(status_code=422, detail="Session has no coach notes yet")

    structured = structure_notes(notes)
    if structured is None:
        structured = _fallback_feedback(notes)

    return FeedbackResponse(**structured)


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
    links = [l.model_dump() for l in payload.links]

    result = organise_evidence(payload.coachId, links)
    if result is None:
        result = _fallback_verification(payload.coachId, links)

    return VerificationResponse(**result)
