from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.mood_builtin_icons import is_valid_builtin_icon_slug
from app.core.mood_scale import (
    MoodScore,
    MoodScoreIconType,
    MoodScoreStyle,
    default_mood_score_style,
    default_mood_score_styles,
    is_valid_hex_color,
    mood_score_emoji,
    mood_score_label,
)
from app.models.user_mood_icon import UserMoodIcon
from app.models.user_mood_preferences import UserMoodPreferences
from app.services.user_provisioning import provision_mood_preferences

_MAX_EMOJI_LENGTH = 8
_MAX_LABEL_LENGTH = 40


class MoodPreferencesError(AppError):
    pass


@dataclass(frozen=True, slots=True)
class ColorDisplaySettings:
    use_historical_colors: bool
    score_colors: dict[int, str]


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
    score_updates: dict[str, dict[str, Any]] | None = None,
    use_historical_colors: bool | None = None,
    show_streak: bool | None = None,
) -> UserMoodPreferences:
    prefs = get_or_create_preferences(db, user_id=user_id)
    if score_updates:
        merged = _merge_score_styles(db, user_id, prefs.score_styles, score_updates)
        prefs.score_styles = merged or None
    if use_historical_colors is not None:
        prefs.use_historical_colors = use_historical_colors
    if show_streak is not None:
        prefs.show_streak = show_streak
    db.commit()
    db.refresh(prefs)
    return prefs


def serialize_preferences(
    db: Session,
    prefs: UserMoodPreferences,
    *,
    locale: str,
) -> dict[str, Any]:
    return {
        "scores": _resolved_score_styles(db, prefs.user_id, prefs.score_styles, locale=locale),
        "use_historical_colors": bool(prefs.use_historical_colors),
        "show_streak": bool(prefs.show_streak),
    }


def get_score_colors(db: Session, *, user_id: uuid.UUID) -> dict[int, str]:
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    return _score_colors_from_styles(prefs.score_styles if prefs is not None else None)


def get_color_display_settings(db: Session, *, user_id: uuid.UUID) -> ColorDisplaySettings:
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    return ColorDisplaySettings(
        use_historical_colors=True if prefs is None else bool(prefs.use_historical_colors),
        score_colors=_score_colors_from_styles(prefs.score_styles if prefs is not None else None),
    )


def _score_colors_from_styles(overrides: dict[str, Any] | None) -> dict[int, str]:
    defaults = default_mood_score_styles()
    result: dict[int, str] = {}
    for score in MoodScore:
        key = str(score.value)
        raw = (overrides or {}).get(key, {})
        color = raw.get("color") if isinstance(raw, dict) else None
        if not isinstance(color, str) or not is_valid_hex_color(color):
            color = defaults[key].color
        result[score.value] = color
    return result


def get_score_label_overrides(db: Session, *, user_id: uuid.UUID) -> dict[str, str]:
    prefs = db.scalar(select(UserMoodPreferences).where(UserMoodPreferences.user_id == user_id))
    return extract_score_label_overrides(prefs.score_styles if prefs is not None else None)


def extract_score_label_overrides(overrides: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, raw in (overrides or {}).items():
        if not isinstance(raw, dict):
            continue
        label = raw.get("label")
        if isinstance(label, str) and label.strip():
            result[str(key)] = label.strip()
    return result


def set_upload_icon_preference(
    db: Session,
    *,
    user_id: uuid.UUID,
    score: MoodScore,
    icon_id: uuid.UUID,
) -> None:
    prefs = get_or_create_preferences(db, user_id=user_id)
    merged = dict(prefs.score_styles or {})
    existing = merged.get(str(score.value), {})
    next_style: dict[str, Any] = {
        "color": existing.get("color", default_mood_score_style(score).color),
        "icon_type": MoodScoreIconType.UPLOAD.value,
        "icon": str(icon_id),
    }
    if isinstance(existing.get("label"), str) and existing["label"].strip():
        next_style["label"] = existing["label"].strip()
    merged[str(score.value)] = next_style
    prefs.score_styles = merged
    db.flush()


def reset_score_to_default_emoji(db: Session, *, user_id: uuid.UUID, score: MoodScore) -> None:
    prefs = get_or_create_preferences(db, user_id=user_id)
    merged = dict(prefs.score_styles or {})
    default_style = default_mood_score_style(score)
    existing = merged.get(str(score.value), {})
    next_style: dict[str, Any] = {
        "color": existing.get("color", default_style.color),
        "icon_type": MoodScoreIconType.EMOJI.value,
        "icon": mood_score_emoji(score),
    }
    if isinstance(existing.get("label"), str) and existing["label"].strip():
        next_style["label"] = existing["label"].strip()
    merged[str(score.value)] = next_style
    prefs.score_styles = merged
    db.flush()


def _resolved_score_styles(
    db: Session,
    user_id: uuid.UUID,
    overrides: dict[str, Any] | None,
    *,
    locale: str,
) -> dict[str, dict[str, str]]:
    defaults = default_mood_score_styles()
    label_overrides = extract_score_label_overrides(overrides)
    resolved: dict[str, dict[str, str]] = {}
    for score in MoodScore:
        key = str(score.value)
        default_style = defaults[key]
        override = (overrides or {}).get(key, {})
        style = _coerce_style(
            db,
            user_id,
            score,
            override,
            default_style,
            strict_upload=False,
        )
        resolved[key] = {
            "color": style.color,
            "icon_type": style.icon_type.value,
            "icon": style.icon,
            "label": label_overrides.get(key) or mood_score_label(score, locale),
        }
    return resolved


def _merge_score_styles(
    db: Session,
    user_id: uuid.UUID,
    current: dict[str, Any] | None,
    updates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(current or {})
    defaults = default_mood_score_styles()

    for raw_score, patch in updates.items():
        score = _parse_score_key(raw_score)
        key = str(score.value)
        default_style = defaults[key]
        existing = dict(merged.get(key, {}))
        next_raw = {**existing, **patch}
        next_style = _coerce_style(
            db,
            user_id,
            score,
            next_raw,
            default_style,
            strict_upload=True,
        )
        stored: dict[str, Any] = {
            "color": next_style.color,
            "icon_type": next_style.icon_type.value,
            "icon": next_style.icon,
        }
        label = _coerce_label(score, next_raw.get("label"), patch_includes_label="label" in patch)
        if label is not None:
            stored["label"] = label
        merged[key] = stored

    return merged


def _coerce_label(score: MoodScore, raw: Any, *, patch_includes_label: bool) -> str | None:
    if not patch_includes_label and raw is None:
        return None
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    if not isinstance(raw, str):
        raise MoodPreferencesError(
            f"Label for score {score.value} must be a string",
            code=ErrorCode.MOOD_LABEL_MUST_BE_STRING,
            params={"score": str(score.value)},
        )
    label = raw.strip()
    if len(label) > _MAX_LABEL_LENGTH:
        raise MoodPreferencesError(
            f"Label for score {score.value} must be at most {_MAX_LABEL_LENGTH} characters",
            code=ErrorCode.MOOD_LABEL_TOO_LONG,
            params={"score": str(score.value), "max": str(_MAX_LABEL_LENGTH)},
        )
    return label


def _coerce_style(
    db: Session,
    user_id: uuid.UUID,
    score: MoodScore,
    raw: dict[str, Any],
    default_style: MoodScoreStyle,
    *,
    strict_upload: bool,
) -> MoodScoreStyle:
    color = raw.get("color", default_style.color)
    if not isinstance(color, str) or not is_valid_hex_color(color):
        raise MoodPreferencesError(
            f"Invalid color for score {score.value}: {color!r}",
            code=ErrorCode.INVALID_MOOD_COLOR,
            params={"score": str(score.value), "color": str(color)},
        )

    icon_type_raw = raw.get("icon_type", default_style.icon_type.value)
    try:
        icon_type = MoodScoreIconType(icon_type_raw)
    except ValueError as exc:
        raise MoodPreferencesError(
            f"Unknown icon type for score {score.value}: {icon_type_raw!r}",
            code=ErrorCode.UNKNOWN_ICON_TYPE,
            params={"score": str(score.value), "icon_type": str(icon_type_raw)},
        ) from exc

    icon = raw.get("icon", default_style.icon)
    if not isinstance(icon, str) or not icon.strip():
        raise MoodPreferencesError(
            f"Icon for score {score.value} must be a non-empty string",
            code=ErrorCode.ICON_REQUIRED,
            params={"score": str(score.value)},
        )
    icon = icon.strip()

    if icon_type is MoodScoreIconType.EMOJI:
        if len(icon) > _MAX_EMOJI_LENGTH:
            raise MoodPreferencesError(
                f"Emoji for score {score.value} must be at most {_MAX_EMOJI_LENGTH} characters",
                code=ErrorCode.EMOJI_TOO_LONG,
                params={"score": str(score.value), "max": str(_MAX_EMOJI_LENGTH)},
            )
    elif icon_type is MoodScoreIconType.BUILTIN:
        if not is_valid_builtin_icon_slug(icon):
            raise MoodPreferencesError(
                f"Unknown built-in icon for score {score.value}: {icon!r}",
                code=ErrorCode.UNKNOWN_BUILTIN_ICON,
                params={"score": str(score.value), "icon": icon},
            )
    elif icon_type is MoodScoreIconType.UPLOAD:
        belongs = _icon_belongs_to_user(db, user_id=user_id, icon_id=icon, score=score)
        if not belongs and strict_upload:
            raise MoodPreferencesError(
                f"Uploaded icon for score {score.value} was not found",
                code=ErrorCode.UPLOADED_ICON_NOT_FOUND,
                status_code=400,
                params={"score": str(score.value)},
            )
        if not belongs:
            return default_mood_score_style(score)
    elif icon_type is MoodScoreIconType.CATALOG:
        from app.services.marketplace_service import can_assign_catalog_icon

        if not can_assign_catalog_icon(db, user_id=user_id, icon_id=icon):
            if strict_upload:
                raise MoodPreferencesError(
                    f"Catalog icon for score {score.value} is not assignable",
                    code=ErrorCode.CATALOG_ICON_NOT_ASSIGNABLE,
                    status_code=400,
                    params={"score": str(score.value)},
                )
            return default_mood_score_style(score)

    return MoodScoreStyle(color=color, icon_type=icon_type, icon=icon)


def _parse_score_key(raw_score: str) -> MoodScore:
    try:
        score = int(raw_score)
        return MoodScore(score)
    except (TypeError, ValueError) as exc:
        raise MoodPreferencesError(
            f"Unknown mood score: {raw_score!r}",
            code=ErrorCode.UNKNOWN_MOOD_SCORE,
            params={"score": str(raw_score)},
        ) from exc


def _icon_belongs_to_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: str,
    score: MoodScore | None = None,
) -> bool:
    try:
        parsed_id = uuid.UUID(icon_id)
    except ValueError:
        return False
    query = select(UserMoodIcon.id).where(
        UserMoodIcon.id == parsed_id,
        UserMoodIcon.user_id == user_id,
    )
    if score is not None:
        query = query.where(UserMoodIcon.score == score.value)
    row = db.scalar(query)
    return row is not None
