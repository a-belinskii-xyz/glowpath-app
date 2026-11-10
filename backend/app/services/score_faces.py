"""One emoji per mood score, for places that can show only text (Telegram buttons).

Kept apart from ``mood_preferences_service`` so the reminder code can use it without
pulling in user provisioning, which itself imports the notifications package.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.emoji import is_single_emoji
from app.core.mood_scale import MoodScore, MoodScoreIconType, mood_score_emoji
from app.models.user_mood_preferences import UserMoodPreferences


def get_score_faces(db: Session, *, user_id: uuid.UUID) -> dict[int, str]:
    """The person's own emoji where they picked one, otherwise the default face."""
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    styles = (prefs.score_styles if prefs is not None else None) or {}
    faces: dict[int, str] = {}
    for score in MoodScore:
        raw = styles.get(str(score.value))
        icon = raw.get("icon") if isinstance(raw, dict) else None
        is_emoji = isinstance(raw, dict) and raw.get("icon_type") == MoodScoreIconType.EMOJI.value
        if is_emoji and isinstance(icon, str) and is_single_emoji(icon):
            faces[score.value] = icon
        else:
            faces[score.value] = mood_score_emoji(score)
    return faces
