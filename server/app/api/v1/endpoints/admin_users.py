"""Admin-only user role workflows."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.models.identity import User
from app.models.enums import GuardianConsentStatus, VerificationStatus
from app.schemas.auth import (
    CoachPromotionRequest,
    CoachVerificationReviewRequest,
    GuardianConsentReviewRequest,
    PublicUser,
)
from app.services.auth import (
    AccountWorkflowError,
    promote_user_to_coach,
    review_coach_verification,
    review_guardian_consent,
)

router = APIRouter(prefix="/admin/users", tags=["user administration"])


@router.post(
    "/{user_id}/promote-to-coach",
    response_model=PublicUser,
    status_code=status.HTTP_201_CREATED,
    summary="Approve and promote a player to coach",
)
def promote_to_coach(
    user_id: UUID,
    payload: CoachPromotionRequest,
    reviewer: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    try:
        return promote_user_to_coach(db, user_id, reviewer, payload.review_notes)
    except AccountWorkflowError as exc:
        code = status.HTTP_404_NOT_FOUND if str(exc) == "User was not found" else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post("/{user_id}/coach-verification", summary="Review an existing coach verification")
def review_coach(
    user_id: UUID,
    payload: CoachVerificationReviewRequest,
    reviewer: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        verification = review_coach_verification(
            db, user_id, reviewer, VerificationStatus(payload.status), payload.review_notes
        )
    except AccountWorkflowError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return {"status": verification.status.value, "reviewed_at": verification.reviewed_at.isoformat()}


@router.post("/{user_id}/guardian-consent", summary="Review a player's guardian consent")
def review_guardian(
    user_id: UUID,
    payload: GuardianConsentReviewRequest,
    reviewer: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        consent = review_guardian_consent(
            db,
            user_id,
            reviewer,
            GuardianConsentStatus(payload.status),
            payload.evidence_reference,
            payload.review_notes,
        )
    except AccountWorkflowError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return {"status": consent.status.value}
