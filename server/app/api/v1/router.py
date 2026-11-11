"""Version 1 route registration."""

from fastapi import APIRouter

from app.api.v1.endpoints.admin_users import router as admin_users_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.profiles import router as profiles_router
from ai.router import router as ai_router
from passport.router import router as passport_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_users_router)
api_router.include_router(profiles_router)
api_router.include_router(ai_router)
api_router.include_router(passport_router)
