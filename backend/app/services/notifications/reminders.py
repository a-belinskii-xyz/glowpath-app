from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.i18n import DEFAULT_LOCALE, normalize_locale, resolve_label
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.models.user_notification_settings import UserNotificationSettings
from app.services.goal_service import goal_is_active_on, week_completion_counts
from app.services.notifications.base import NotificationChannel
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.messages import (
    daily_mood_reminder_message,
    goal_reminder_message,
)


@dataclass(slots=True)
class ReminderRunStats:
    users_considered: int = 0
    daily_mood_sent: int = 0
    goal_reminders_sent: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def process_due_reminders(
    db: Session,
    dispatcher: NotificationDispatcher,
    *,
    now: datetime | None = None,
) -> ReminderRunStats:
    """Send due daily mood and goal reminders for users who opted in."""
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)

    stats = ReminderRunStats()
    user_ids = list(
        db.scalars(
            select(UserNotificationSettings.user_id).where(
                UserNotificationSettings.enabled.is_(True)
            )
        ).all()
    )
    window = timedelta(minutes=settings.notifications_match_window_minutes)

    for user_id in user_ids:
        stats.users_considered += 1
        prefs = db.scalar(
            select(UserNotificationSettings)
            .where(UserNotificationSettings.user_id == user_id)
            .options(joinedload(UserNotificationSettings.user))
        )
        if prefs is None:
            stats.skipped += 1
            continue

        user = prefs.user
        if user.email_verified_at is None:
            stats.skipped += 1
            continue

        try:
            tz = ZoneInfo(user.timezone)
        except ZoneInfoNotFoundError:
            stats.errors.append(f"user={user.id}: unknown timezone {user.timezone!r}")
            continue

        local_now = instant.astimezone(tz)
        local_day = local_now.date()
        channels = _parse_channels(prefs.channels)
        if not channels or prefs.daily_mood_reminder_time is None:
            stats.skipped += 1
            continue

        if not _is_within_reminder_window(
            local_now=local_now,
            reminder_time=prefs.daily_mood_reminder_time,
            window=window,
        ):
            stats.skipped += 1
            continue

        try:
            deliverable = _deliverable_channels(user, channels)
            if not deliverable:
                stats.skipped += 1
                continue
            _process_user_reminders(
                db,
                dispatcher,
                prefs=prefs,
                user=user,
                channels=deliverable,
                local_day=local_day,
                local_hour=local_now.hour,
                tz=tz,
                stats=stats,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            stats.errors.append(f"user={user.id}: {exc}")

    return stats


def _process_user_reminders(
    db: Session,
    dispatcher: NotificationDispatcher,
    *,
    prefs: UserNotificationSettings,
    user: User,
    channels: list[NotificationChannel],
    local_day: date,
    local_hour: int,
    tz: ZoneInfo,
    stats: ReminderRunStats,
) -> None:
    locale = normalize_locale(user.telegram_locale) if user.telegram_locale else DEFAULT_LOCALE
    if prefs.daily_mood_reminder_enabled and prefs.last_daily_mood_reminder_on != local_day:
        if _has_mood_entry_on_local_day(db, user=user, local_day=local_day, tz=tz):
            prefs.last_daily_mood_reminder_on = local_day
        else:
            for channel in channels:
                dispatcher.send(
                    user=user,
                    channels=[channel],
                    message=daily_mood_reminder_message(
                        channel=channel,
                        hour=local_hour,
                        locale=locale,
                    ),
                )
            prefs.last_daily_mood_reminder_on = local_day
            stats.daily_mood_sent += 1

    if prefs.goal_reminders_enabled and prefs.last_goal_reminder_on != local_day:
        behind = _behind_goals(db, user=user, local_day=local_day)
        if behind:
            labels = [resolve_label(goal.labels, DEFAULT_LOCALE) for goal in behind]
            for channel in channels:
                dispatcher.send(
                    user=user,
                    channels=[channel],
                    message=goal_reminder_message(channel=channel, goal_labels=labels),
                )
            prefs.last_goal_reminder_on = local_day
            stats.goal_reminders_sent += 1
        else:
            prefs.last_goal_reminder_on = local_day


def _parse_channels(raw: list[str]) -> list[NotificationChannel]:
    channels: list[NotificationChannel] = []
    for value in raw:
        try:
            channel = NotificationChannel(value)
        except ValueError:
            continue
        if channel not in channels:
            channels.append(channel)
    return channels


def _deliverable_channels(
    user: User,
    channels: list[NotificationChannel],
) -> list[NotificationChannel]:
    """Drop channels that cannot be delivered for this user right now."""
    deliverable: list[NotificationChannel] = []
    for channel in channels:
        if channel is NotificationChannel.TELEGRAM and not user.telegram_linked:
            continue
        deliverable.append(channel)
    return deliverable


def _is_within_reminder_window(
    *,
    local_now: datetime,
    reminder_time: time,
    window: timedelta,
) -> bool:
    start = local_now.replace(
        hour=reminder_time.hour,
        minute=reminder_time.minute,
        second=0,
        microsecond=0,
    )
    end = start + window
    return start <= local_now < end


def _has_mood_entry_on_local_day(
    db: Session,
    *,
    user: User,
    local_day: date,
    tz: ZoneInfo,
) -> bool:
    day_start = datetime.combine(local_day, time.min, tzinfo=tz).astimezone(UTC)
    day_end = day_start + timedelta(days=1)
    entry_id = db.scalar(
        select(MoodEntry.id)
        .where(
            MoodEntry.user_id == user.id,
            MoodEntry.recorded_at >= day_start,
            MoodEntry.recorded_at < day_end,
        )
        .limit(1)
    )
    return entry_id is not None


def _behind_goals(db: Session, *, user: User, local_day: date) -> list[Goal]:
    goals = list(
        db.scalars(
            select(Goal)
            .where(Goal.user_id == user.id, Goal.starts_on <= local_day)
            .order_by(Goal.sort_order, Goal.slug)
        ).all()
    )
    goals = [goal for goal in goals if goal_is_active_on(goal, local_day)]
    if not goals:
        return []

    counts = week_completion_counts(
        db,
        user_id=user.id,
        timezone_name=user.timezone,
        goal_ids=[goal.id for goal in goals],
        reference_date=local_day,
    )
    return [goal for goal in goals if counts.get(goal.id, 0) < goal.times_per_week]
