from fastapi import APIRouter

from app.api.v1 import (
    achievements,
    auth,
    goals,
    health,
    marketplace,
    mood_entries,
    mood_preferences,
    note_templates,
    notification_settings,
    onboarding,
    tag_groups,
    telegram,
    wallet,
)
from app.config import settings

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(onboarding.router, prefix="/onboarding")
api_v1_router.include_router(mood_entries.router, prefix="/mood-entries")
api_v1_router.include_router(note_templates.router, prefix="/note-templates")
api_v1_router.include_router(tag_groups.router, prefix="/tag-groups")
api_v1_router.include_router(goals.router, prefix="/goals")
api_v1_router.include_router(notification_settings.router, prefix="/notification-settings")
api_v1_router.include_router(mood_preferences.router, prefix="/mood-preferences")
api_v1_router.include_router(marketplace.router, prefix="/marketplace")
api_v1_router.include_router(wallet.router, prefix="/wallet")
api_v1_router.include_router(achievements.router, prefix="/achievements")
api_v1_router.include_router(telegram.router, prefix="/telegram")

if settings.debug:
    from app.api.v1 import auth_dev

    api_v1_router.include_router(auth_dev.router, prefix="/dev/auth")
