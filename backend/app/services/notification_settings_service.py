from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.schemas.notification_settings import (
    DEFAULT_TIME_BY_KIND,
    PROVISIONED_KINDS,
    NotificationScheduleKind,
    NotificationSchedulePublic,
    NotificationScheduleUpdate,
    NotificationSettingsPublic,
)
from app.services.notifications.backoff import resume_schedule
from app.services.notifications.base import NotificationChannel
from app.services.notifications.worker_status import system_status
from app.services.user_provisioning import provision_notification_settings


class NotificationSettingsError(AppError):
    pass


_IMPLEMENTED_CHANNELS = frozenset({NotificationChannel.EMAIL, NotificationChannel.TELEGRAM})
_KIND_ORDER = {kind: index for index, kind in enumerate(NotificationScheduleKind)}


def list_settings(
    db: Session,
    *,
    user_id: uuid.UUID,
    locale: str,
) -> NotificationSettingsPublic:
    rows = ensure_schedules(db, user_id=user_id)
    return NotificationSettingsPublic(
        system_status=system_status(db, locale=locale),
        schedules=[_serialize(row) for row in rows],
    )


def ensure_schedules(db: Session, *, user_id: uuid.UUID) -> list[UserNotificationSchedule]:
    rows = list(
        db.scalars(
            select(UserNotificationSchedule).where(UserNotificationSchedule.user_id == user_id)
        ).all()
    )
    kinds = {row.kind for row in rows}
    missing = [kind for kind in PROVISIONED_KINDS if kind.value not in kinds]
    if not rows or missing:
        provision_notification_settings(db, user_id)
        db.commit()
        rows = list(
            db.scalars(
                select(UserNotificationSchedule).where(UserNotificationSchedule.user_id == user_id)
            ).all()
        )
    elif _heal_telegram_native_channels(db, rows, user_id=user_id):
        db.commit()
        for row in rows:
            db.refresh(row)
    return sorted(rows, key=lambda row: _KIND_ORDER.get(NotificationScheduleKind(row.kind), 99))


def update_schedule(
    db: Session,
    *,
    user_id: uuid.UUID,
    kind: str,
    body: NotificationScheduleUpdate,
    locale: str,
) -> NotificationSettingsPublic:
    if not settings.feature_notifications_enabled:
        raise NotificationSettingsError(
            "Notifications are disabled while the app is in closed testing",
            code=ErrorCode.FEATURE_DISABLED,
            status_code=403,
        )
    try:
        schedule_kind = NotificationScheduleKind(kind)
    except ValueError as exc:
        raise NotificationSettingsError(
            f"Unknown notification kind: {kind}",
            code=ErrorCode.UNKNOWN_NOTIFICATION_KIND,
            status_code=404,
            params={"kind": kind},
        ) from exc

    rows = ensure_schedules(db, user_id=user_id)
    row = next((item for item in rows if item.kind == schedule_kind.value), None)
    if row is None:
        row = UserNotificationSchedule(
            user_id=user_id,
            kind=schedule_kind.value,
            enabled=False,
            time_of_day=DEFAULT_TIME_BY_KIND[schedule_kind],
            interval_days=1,
            channels=_default_channels(db, user_id),
        )
        db.add(row)
        db.flush()

    if body.enabled is not None:
        row.enabled = body.enabled
        if body.enabled and row.paused_at is not None:
            resume_schedule(row, at=datetime.now(UTC))
    if body.time_of_day is not None:
        row.time_of_day = body.time_of_day
    if body.interval_days is not None:
        row.interval_days = body.interval_days
    if "days_of_week" in body.model_fields_set:
        row.days_of_week = body.days_of_week or None
    if body.channels is not None:
        row.channels = _serialize_channels(body.channels, user_id=user_id, db=db)

    _validate_row(row, user_id=user_id, db=db)
    db.commit()
    db.refresh(row)
    return list_settings(db, user_id=user_id, locale=locale)


def enable_daily_email_reminder(db: Session, *, user: User) -> bool:
    """Opt-in from onboarding: daily mood reminder by email at the default time.

    Only for accounts that have a verified email and no Telegram (Telegram users get
    reminders in the bot). Does nothing while notifications are switched off.
    """
    if not settings.feature_notifications_enabled:
        return False
    if not user.email or user.email_verified_at is None or user.telegram_linked:
        return False
    rows = ensure_schedules(db, user_id=user.id)
    row = next(item for item in rows if item.kind == NotificationScheduleKind.DAILY_MOOD.value)
    row.enabled = True
    row.channels = [NotificationChannel.EMAIL.value]
    if row.paused_at is not None:
        resume_schedule(row, at=datetime.now(UTC))
    return True


def unsubscribe_email(db: Session, *, user_id: uuid.UUID) -> int:
    """Stop all email reminders for a user (unsubscribe link and one-click header).

    Email is dropped from multi-channel schedules; email-only schedules are switched off
    so the channel list stays valid. Returns how many schedules changed.
    """
    rows = db.scalars(
        select(UserNotificationSchedule).where(UserNotificationSchedule.user_id == user_id)
    ).all()
    changed = 0
    email = NotificationChannel.EMAIL.value
    for row in rows:
        channels = list(row.channels or [])
        if email not in channels:
            continue
        others = [channel for channel in channels if channel != email]
        if others:
            row.channels = others
        elif row.enabled:
            row.enabled = False
        else:
            continue
        changed += 1
    db.commit()
    return changed


def serialize_schedule(row: UserNotificationSchedule) -> dict[str, Any]:
    return _serialize(row).model_dump(mode="json")


def _serialize(row: UserNotificationSchedule) -> NotificationSchedulePublic:
    return NotificationSchedulePublic(
        kind=NotificationScheduleKind(row.kind),
        enabled=row.enabled and row.paused_at is None,
        time_of_day=row.time_of_day,
        interval_days=row.interval_days,
        days_of_week=list(row.days_of_week) if row.days_of_week else None,
        channels=[NotificationChannel(channel) for channel in row.channels],
        last_sent_at=row.last_sent_at,
        paused_at=row.paused_at,
    )


def _default_channels(db: Session, user_id: uuid.UUID) -> list[str]:
    user = db.get(User, user_id)
    if user is not None and user.telegram_linked:
        return [NotificationChannel.TELEGRAM.value]
    return [NotificationChannel.EMAIL.value]


def _serialize_channels(
    channels: list[NotificationChannel],
    *,
    user_id: uuid.UUID,
    db: Session,
) -> list[str]:
    if not channels:
        raise NotificationSettingsError(
            "At least one notification channel is required",
            code=ErrorCode.NOTIFICATION_CHANNEL_REQUIRED,
        )
    unique: list[str] = []
    for channel in channels:
        if channel not in _IMPLEMENTED_CHANNELS:
            raise NotificationSettingsError(
                f"Notification channel is not available yet: {channel}",
                code=ErrorCode.NOTIFICATION_CHANNEL_UNAVAILABLE,
                status_code=400,
                params={"channel": str(channel)},
            )
        if channel is NotificationChannel.TELEGRAM:
            _require_telegram_linked(db, user_id=user_id)
        if channel.value not in unique:
            unique.append(channel.value)
    return unique


def _validate_row(
    row: UserNotificationSchedule,
    *,
    user_id: uuid.UUID,
    db: Session,
) -> None:
    channels = row.channels or []
    if not channels:
        raise NotificationSettingsError(
            "At least one notification channel is required",
            code=ErrorCode.NOTIFICATION_CHANNEL_REQUIRED,
        )
    for raw in channels:
        try:
            channel = NotificationChannel(raw)
        except ValueError as exc:
            raise NotificationSettingsError(
                f"Unknown notification channel: {raw}",
                code=ErrorCode.UNKNOWN_NOTIFICATION_CHANNEL,
                params={"channel": str(raw)},
            ) from exc
        if channel not in _IMPLEMENTED_CHANNELS:
            raise NotificationSettingsError(
                f"Notification channel is not available yet: {channel}",
                code=ErrorCode.NOTIFICATION_CHANNEL_UNAVAILABLE,
                status_code=400,
                params={"channel": str(channel)},
            )
        if channel is NotificationChannel.TELEGRAM:
            _require_telegram_linked(db, user_id=user_id)
    if row.interval_days < 1:
        raise NotificationSettingsError(
            "interval_days must be at least 1",
            code=ErrorCode.INVALID_INTERVAL_DAYS,
        )


def _heal_telegram_native_channels(
    db: Session,
    rows: list[UserNotificationSchedule],
    *,
    user_id: uuid.UUID,
) -> bool:
    """Telegram-only accounts should not keep an undeliverable email channel."""
    user = db.get(User, user_id)
    if user is None or user.email or not user.telegram_linked:
        return False
    desired = [NotificationChannel.TELEGRAM.value]
    changed = False
    for row in rows:
        if list(row.channels or []) == desired:
            continue
        row.channels = desired
        changed = True
    return changed


def _require_telegram_linked(db: Session, *, user_id: uuid.UUID) -> None:
    user = db.get(User, user_id)
    if user is None or not user.telegram_linked:
        raise NotificationSettingsError(
            "Link Telegram in your profile before enabling that channel",
            code=ErrorCode.TELEGRAM_LINK_REQUIRED,
            status_code=400,
        )
