from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import TagGroupListResponse, TagGroupPublic
from app.services.mood_entry_service import list_tag_groups, serialize_tag_groups

router = APIRouter(tags=["tag-groups"])


@router.get("", response_model=TagGroupListResponse)
def get_tag_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> TagGroupListResponse:
    groups = list_tag_groups(db, user_id=current_user.id)
    items = [
        TagGroupPublic.model_validate(item) for item in serialize_tag_groups(groups, locale=locale)
    ]
    return TagGroupListResponse(items=items)
