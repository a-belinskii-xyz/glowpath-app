from fastapi import APIRouter

from app.api.v1 import auth, goals, health, mood_entries, note_templates, tag_groups
from app.config import settings

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(mood_entries.router, prefix="/mood-entries")
api_v1_router.include_router(note_templates.router, prefix="/note-templates")
api_v1_router.include_router(tag_groups.router, prefix="/tag-groups")
api_v1_router.include_router(goals.router, prefix="/goals")

if settings.debug:
    from app.api.v1 import auth_dev

    api_v1_router.include_router(auth_dev.router, prefix="/dev/auth")
