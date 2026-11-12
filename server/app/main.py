"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — origins are read from CORS_ORIGINS env var (comma-separated).
# Defaults to local dev origins. Never use "*" with allow_credentials=True.
_allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> dict:
    """Service identity — used by uptime monitors and smoke tests."""
    return {"status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
def root_health() -> dict:
    """Shallow liveness check at the root path (no DB required)."""
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error_handler(
    request, exc: RequestValidationError
) -> JSONResponse:
    """Omit submitted values from validation errors, including password inputs."""
    details = [
        {"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})
