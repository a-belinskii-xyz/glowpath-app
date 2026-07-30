from __future__ import annotations

import uuid
from datetime import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.user import User
from app.models.user_notification_settings import UserNotificationSettings
from app.services.notifications.base import NotificationChannel
from app.services.user_provisioning import provision_notification_settings


class NotificationSettingsError(AppError):
    pass


_IMPLEMENTED_CHANNELS = frozenset({NotificationChannel.EMAIL, NotificationChannel.TELEGRAM})


def get_or_create_settings(db: Session, *, user_id: uuid.UUID) -> UserNotificationSettings:
    settings_row = db.scalar(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    if settings_row is not None:
        return settings_row
    provision_notification_settings(db, user_id)
    db.commit()
    settings_row = db.scalar(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    assert settings_row is not None
    return settings_row


def update_settings(
    db: Session,
    *,
    user_id: uuid.UUID,
    enabled: bool | None = None,
    channels: list[NotificationChannel] | None = None,
    daily_mood_reminder_enabled: bool | None = None,
    daily_mood_reminder_time: time | None = None,
    clear_daily_mood_reminder_time: bool = False,
    goal_reminders_enabled: bool | None = None,
) -> UserNotificationSettings:
    prefs = get_or_create_settings(db, user_id=user_id)

    if enabled is not None:
        prefs.enabled = enabled
    if channels is not None:
        prefs.channels = _serialize_channels(channels, user_id=user_id, db=db)
    if daily_mood_reminder_enabled is not None:
        prefs.daily_mood_reminder_enabled = daily_mood_reminder_enabled
    if clear_daily_mood_reminder_time:
        prefs.daily_mood_reminder_time = None
    elif daily_mood_reminder_time is not None:
        prefs.daily_mood_reminder_time = daily_mood_reminder_time
    if goal_reminders_enabled is not None:
        prefs.goal_reminders_enabled = goal_reminders_enabled

    _validate_prefs(prefs, user_id=user_id, db=db)
    db.commit()
    db.refresh(prefs)
    return prefs


def serialize_settings(prefs: UserNotificationSettings) -> dict[str, Any]:
    return {
        "enabled": prefs.enabled,
        "channels": list(prefs.channels),
        "daily_mood_reminder_enabled": prefs.daily_mood_reminder_enabled,
        "daily_mood_reminder_time": prefs.daily_mood_reminder_time,
        "goal_reminders_enabled": prefs.goal_reminders_enabled,
    }


def _serialize_channels(
    channels: list[NotificationChannel],
    *,
    user_id: uuid.UUID,
    db: Session,
) -> list[str]:
    if not channels:
        raise NotificationSettingsError(
            "At least one notification channel is required", code="notification_channel_required"
        )
    unique: list[str] = []
    for channel in channels:
        if channel not in _IMPLEMENTED_CHANNELS:
            raise NotificationSettingsError(
                f"Notification channel is not available yet: {channel}",
                code="notification_channel_unavailable",
                status_code=400,
                params={"channel": str(channel)},
            )
        if channel is NotificationChannel.TELEGRAM:
            _require_telegram_linked(db, user_id=user_id)
        if channel.value not in unique:
            unique.append(channel.value)
    return unique


def _validate_prefs(
    prefs: UserNotificationSettings,
    *,
    user_id: uuid.UUID,
    db: Session,
) -> None:
    channels = prefs.channels or []
    if not channels:
        raise NotificationSettingsError(
            "At least one notification channel is required", code="notification_channel_required"
        )
    for raw in channels:
        try:
            channel = NotificationChannel(raw)
        except ValueError as exc:
            raise NotificationSettingsError(
                f"Unknown notification channel: {raw}",
                code="unknown_notification_channel",
                params={"channel": str(raw)},
            ) from exc
        if channel not in _IMPLEMENTED_CHANNELS:
            raise NotificationSettingsError(
                f"Notification channel is not available yet: {channel}",
                code="notification_channel_unavailable",
                status_code=400,
                params={"channel": str(channel)},
            )
        if channel is NotificationChannel.TELEGRAM:
            _require_telegram_linked(db, user_id=user_id)

    needs_schedule = prefs.daily_mood_reminder_enabled or prefs.goal_reminders_enabled
    if prefs.enabled and needs_schedule and prefs.daily_mood_reminder_time is None:
        raise NotificationSettingsError(
            "daily_mood_reminder_time is required when mood or goal reminders are enabled",
            code="reminder_time_required",
        )


def _require_telegram_linked(db: Session, *, user_id: uuid.UUID) -> None:
    user = db.get(User, user_id)
    if user is None or not user.telegram_linked:
        raise NotificationSettingsError(
            "Link Telegram in your profile before enabling that channel",
            code="telegram_link_required",
            status_code=400,
        )
