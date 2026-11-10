"""Admin-only user role workflows."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.models.identity import User
from app.schemas.auth import CoachPromotionRequest, PublicUser
from app.services.auth import AccountWorkflowError, promote_user_to_coach

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
