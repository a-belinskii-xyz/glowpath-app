from fastapi import APIRouter

from app.api.v1 import auth, health
from app.config import settings

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router, prefix="/auth")

if settings.debug:
    from app.api.v1 import auth_dev

    api_v1_router.include_router(auth_dev.router, prefix="/dev/auth")
