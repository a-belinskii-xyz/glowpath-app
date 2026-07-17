from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mood_scale import (
    MoodScore,
    MoodScoreIconType,
    MoodScoreStyle,
    default_mood_score_styles,
    is_valid_hex_color,
)
from app.models.user_mood_preferences import UserMoodPreferences
from app.services.user_provisioning import provision_mood_preferences


class MoodPreferencesError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_or_create_preferences(db: Session, *, user_id: uuid.UUID) -> UserMoodPreferences:
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    if prefs is not None:
        return prefs
    provision_mood_preferences(db, user_id)
    db.commit()
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    assert prefs is not None
    return prefs


def update_preferences(
    db: Session,
    *,
    user_id: uuid.UUID,
    score_updates: dict[str, dict[str, Any]],
) -> UserMoodPreferences:
    prefs = get_or_create_preferences(db, user_id=user_id)
    merged = _merge_score_styles(prefs.score_styles, score_updates)
    prefs.score_styles = merged or None
    db.commit()
    db.refresh(prefs)
    return prefs


def serialize_preferences(prefs: UserMoodPreferences) -> dict[str, Any]:
    return {"scores": _resolved_score_styles(prefs.score_styles)}


def _resolved_score_styles(overrides: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    defaults = default_mood_score_styles()
    resolved: dict[str, dict[str, str]] = {}
    for score in MoodScore:
        key = str(score.value)
        default_style = defaults[key]
        override = (overrides or {}).get(key, {})
        style = _coerce_style(score, override, default_style)
        resolved[key] = {
            "color": style.color,
            "icon_type": style.icon_type.value,
            "icon": style.icon,
        }
    return resolved


def _merge_score_styles(
    current: dict[str, Any] | None,
    updates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(current or {})
    defaults = default_mood_score_styles()

    for raw_score, patch in updates.items():
        score = _parse_score_key(raw_score)
        default_style = defaults[str(score.value)]
        existing = merged.get(str(score.value), {})
        next_style = _coerce_style(score, {**existing, **patch}, default_style)
        merged[str(score.value)] = {
            "color": next_style.color,
            "icon_type": next_style.icon_type.value,
            "icon": next_style.icon,
        }

    return merged


def _coerce_style(
    score: MoodScore,
    raw: dict[str, Any],
    default_style: MoodScoreStyle,
) -> MoodScoreStyle:
    color = raw.get("color", default_style.color)
    if not isinstance(color, str) or not is_valid_hex_color(color):
        raise MoodPreferencesError(f"Invalid color for score {score.value}: {color!r}")

    icon_type_raw = raw.get("icon_type", default_style.icon_type.value)
    try:
        icon_type = MoodScoreIconType(icon_type_raw)
    except ValueError as exc:
        raise MoodPreferencesError(
            f"Unknown icon type for score {score.value}: {icon_type_raw!r}"
        ) from exc

    icon = raw.get("icon", default_style.icon)
    if not isinstance(icon, str) or not icon.strip():
        raise MoodPreferencesError(f"Icon for score {score.value} must be a non-empty string")

    if icon_type is MoodScoreIconType.UPLOAD:
        raise MoodPreferencesError(
            f"Custom uploaded icons are not available yet for score {score.value}",
            status_code=400,
        )

    return MoodScoreStyle(color=color, icon_type=icon_type, icon=icon.strip())


def _parse_score_key(raw_score: str) -> MoodScore:
    try:
        score = int(raw_score)
        return MoodScore(score)
    except (TypeError, ValueError) as exc:
        raise MoodPreferencesError(f"Unknown mood score: {raw_score!r}") from exc
