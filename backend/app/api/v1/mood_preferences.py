from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.mood_preferences import MoodPreferencesPublic, MoodPreferencesUpdate
from app.services.mood_preferences_service import (
    MoodPreferencesError,
    get_or_create_preferences,
    serialize_preferences,
    update_preferences,
)

router = APIRouter(tags=["mood-preferences"])


@router.get("", response_model=MoodPreferencesPublic)
def get_mood_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> MoodPreferencesPublic:
    prefs = get_or_create_preferences(db, user_id=current_user.id)
    return MoodPreferencesPublic.model_validate(serialize_preferences(prefs))


@router.patch("", response_model=MoodPreferencesPublic)
def patch_mood_preferences(
    body: MoodPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> MoodPreferencesPublic:
    updates = {score: patch.model_dump(exclude_unset=True) for score, patch in body.scores.items()}
    try:
        prefs = update_preferences(db, user_id=current_user.id, score_updates=updates)
    except MoodPreferencesError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return MoodPreferencesPublic.model_validate(serialize_preferences(prefs))
