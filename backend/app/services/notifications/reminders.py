from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.i18n import DEFAULT_LOCALE, normalize_locale, resolve_label
from app.core.identity import user_has_verified_identity
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
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
    """Send due mood and goal reminders for schedules whose local time matches."""
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    if not settings.feature_notifications_enabled:
        return ReminderRunStats()

    stats = ReminderRunStats()
    schedules = list(
        db.scalars(
            select(UserNotificationSchedule)
            .where(UserNotificationSchedule.enabled.is_(True))
            .options(joinedload(UserNotificationSchedule.user))
        ).unique().all()
    )
    window = timedelta(minutes=settings.notifications_match_window_minutes)

    for schedule in schedules:
        stats.users_considered += 1
        user = schedule.user
        if not user_has_verified_identity(user):
            stats.skipped += 1
            continue

        try:
            tz = ZoneInfo(user.timezone)
        except ZoneInfoNotFoundError:
            stats.errors.append(f"user={user.id}: unknown timezone {user.timezone!r}")
            continue

        local_now = instant.astimezone(tz)
        try:
            reminder_clock = _parse_time_of_day(schedule.time_of_day)
        except ValueError:
            stats.errors.append(f"user={user.id}: bad time_of_day {schedule.time_of_day!r}")
            continue

        if not _is_within_reminder_window(
            local_now=local_now,
            reminder_time=reminder_clock,
            window=window,
        ):
            stats.skipped += 1
            continue
        if not _schedule_is_due(schedule, local_day=local_now.date(), tz=tz):
            stats.skipped += 1
            continue

        channels = _parse_channels(schedule.channels)
        if schedule.kind not in {"daily_mood", "goal_tracking"}:
            stats.skipped += 1
            continue
        deliverable = _deliverable_channels(user, channels)
        if not deliverable:
            stats.skipped += 1
            continue

        try:
            sent = _deliver_schedule(
                db,
                dispatcher,
                schedule=schedule,
                user=user,
                channels=deliverable,
                local_day=local_now.date(),
                local_hour=local_now.hour,
                tz=tz,
            )
            if sent:
                if schedule.kind == "daily_mood":
                    stats.daily_mood_sent += 1
                elif schedule.kind == "goal_tracking":
                    stats.goal_reminders_sent += 1
            else:
                stats.skipped += 1
            schedule.last_sent_at = instant
            db.commit()
        except Exception as exc:
            db.rollback()
            stats.errors.append(f"user={user.id}: {exc}")

    return stats


def _schedule_is_due(
    schedule: UserNotificationSchedule,
    *,
    local_day: date,
    tz: ZoneInfo,
) -> bool:
    weekdays = list(schedule.days_of_week or [])
    if weekdays and local_day.weekday() not in weekdays:
        return False
    if schedule.last_sent_at is None:
        return True
    last_sent = schedule.last_sent_at
    if last_sent.tzinfo is None:
        last_sent = last_sent.replace(tzinfo=UTC)
    last_local_day = last_sent.astimezone(tz).date()
    return (local_day - last_local_day).days >= schedule.interval_days


def _parse_time_of_day(value: str) -> time:
    from app.schemas.notification_settings import normalize_time_of_day

    normalized = normalize_time_of_day(value)
    hour, minute = normalized.split(":")
    return time(int(hour), int(minute))


def _deliver_schedule(
    db: Session,
    dispatcher: NotificationDispatcher,
    *,
    schedule: UserNotificationSchedule,
    user: User,
    channels: list[NotificationChannel],
    local_day: date,
    local_hour: int,
    tz: ZoneInfo,
) -> bool:
    locale = normalize_locale(user.telegram_locale) if user.telegram_locale else DEFAULT_LOCALE
    if schedule.kind == "daily_mood":
        if _has_mood_entry_on_local_day(db, user=user, local_day=local_day, tz=tz):
            return False
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
        return True

    if schedule.kind == "goal_tracking":
        behind = _behind_goals(db, user=user, local_day=local_day)
        if not behind:
            return False
        labels = [resolve_label(goal.labels, DEFAULT_LOCALE) for goal in behind]
        for channel in channels:
            dispatcher.send(
                user=user,
                channels=[channel],
                message=goal_reminder_message(
                    channel=channel,
                    goal_labels=labels,
                    locale=locale,
                ),
            )
        return True

    return False


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
        if channel is NotificationChannel.EMAIL and not user.email:
            continue
        if channel is NotificationChannel.TELEGRAM and not user.telegram_linked:
            continue
        if channel not in deliverable:
            deliverable.append(channel)
    if deliverable:
        return deliverable
    if user.telegram_linked:
        return [NotificationChannel.TELEGRAM]
    if user.email:
        return [NotificationChannel.EMAIL]
    return []


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
