"""Health endpoint used by Render and local development."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_database_connection

router = APIRouter()


@router.get("/health", summary="Check API and database health")
def health_check() -> dict[str, str]:
    """Return healthy only when the application can reach its database."""
    try:
        check_database_connection()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ok", "database": "ok"}
