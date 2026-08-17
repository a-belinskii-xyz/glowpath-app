from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.i18n import DEFAULT_LOCALE, normalize_locale
from app.core.mood_scale import MoodScore, MoodScoreIconType, mood_score_emoji
from app.models.mood_entry import MoodEntry
from app.models.telegram_session import TelegramSession
from app.models.user import User
from app.services.goal_service import goal_is_active_on, list_goals, serialize_goal
from app.services.mood_entry_service import create_mood_entry
from app.services.mood_preferences_service import get_or_create_preferences, serialize_preferences
from app.services.tag_service import list_tag_groups, serialize_tag_group
from app.services.telegram_link_service import get_user_by_telegram_id


class TelegramBotError(AppError):
    pass


def require_linked_user(db: Session, *, telegram_user_id: int) -> User:
    user = get_user_by_telegram_id(db, telegram_user_id=telegram_user_id)
    if user is None:
        raise TelegramBotError(
            "Telegram account is not linked", code=ErrorCode.TELEGRAM_NOT_LINKED, status_code=404
        )
    return user


def resolve_bot_locale(user: User, *, locale: str | None = None) -> str:
    if locale:
        return normalize_locale(locale)
    if user.telegram_locale:
        return normalize_locale(user.telegram_locale)
    return DEFAULT_LOCALE


def _user_zone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def build_catalog(db: Session, *, user: User, locale: str | None = None) -> dict[str, Any]:
    resolved_locale = resolve_bot_locale(user, locale=locale)
    prefs = get_or_create_preferences(db, user_id=user.id)
    scores_map = serialize_preferences(db, prefs, locale=resolved_locale)["scores"]

    scores: list[dict[str, Any]] = []
    for score in MoodScore:
        style = scores_map[str(score.value)]
        icon_type = style["icon_type"]
        icon = style["icon"]
        emoji = icon if icon_type == MoodScoreIconType.EMOJI.value else mood_score_emoji(score)
        scores.append(
            {
                "score": score.value,
                "label": style["label"],
                "emoji": emoji,
                "color": style["color"],
                "icon_type": icon_type,
                "icon": icon,
            }
        )

    tag_groups = [
        serialize_tag_group(group, locale=resolved_locale)
        for group in list_tag_groups(db, user_id=user.id)
        if group.show_on_entry
    ]

    today = datetime.now(UTC).astimezone(_user_zone(user)).date()
    goals = [
        serialize_goal(goal, locale=resolved_locale)
        for goal in list_goals(db, user_id=user.id)
        if goal.show_on_entry and goal_is_active_on(goal, today)
    ]

    return {
        "locale": resolved_locale,
        "timezone": user.timezone,
        "scores": scores,
        "tag_groups": tag_groups,
        "goals": goals,
    }


def create_entry_for_telegram_user(
    db: Session,
    *,
    user: User,
    score: int,
    tag_ids: list[uuid.UUID],
    goal_ids: list[uuid.UUID],
    note: str | None,
    source: str | None,
) -> MoodEntry:
    return create_mood_entry(
        db,
        user_id=user.id,
        score=score,
        recorded_at=datetime.now(UTC),
        note=note,
        tag_ids=tag_ids,
        goal_ids=goal_ids,
        source=source,
        fill_quantity_from_target=True,
    )


def get_session(db: Session, *, telegram_user_id: int) -> TelegramSession | None:
    return db.get(TelegramSession, telegram_user_id)


def upsert_session(
    db: Session,
    *,
    telegram_user_id: int,
    state: dict[str, Any],
) -> TelegramSession:
    row = db.get(TelegramSession, telegram_user_id)
    if row is None:
        row = TelegramSession(telegram_user_id=telegram_user_id, state=state)
        db.add(row)
    else:
        row.state = state
    db.commit()
    db.refresh(row)
    return row


def delete_session(db: Session, *, telegram_user_id: int) -> bool:
    row = db.get(TelegramSession, telegram_user_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def serialize_session(row: TelegramSession | None, *, telegram_user_id: int) -> dict[str, Any]:
    if row is None:
        return {
            "telegram_user_id": telegram_user_id,
            "state": {},
            "updated_at": None,
        }
    return {
        "telegram_user_id": row.telegram_user_id,
        "state": row.state or {},
        "updated_at": row.updated_at,
    }
