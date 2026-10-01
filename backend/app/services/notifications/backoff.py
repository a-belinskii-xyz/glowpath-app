"""Send reminders less often when people ignore them, then stop.

A delivery counts as answered when the person followed its link (``engaged_at``) or
made an entry before the next reminder went out. Unanswered deliveries in a row form
the ignored streak, which stretches the gap between reminders and finally pauses the
schedule. Any answer resets the streak.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.mood_entry import MoodEntry
from app.models.notification_delivery import NotificationDelivery
from app.models.user_notification_schedule import UserNotificationSchedule

# Ignored streak -> minimum days between reminders. Beyond the table the schedule pauses.
_GAP_DAYS_BY_STREAK = (1, 1, 2, 4, 4, 7, 7)
PAUSE_AFTER_IGNORED = len(_GAP_DAYS_BY_STREAK)


@dataclass(frozen=True, slots=True)
class BackoffState:
    ignored_streak: int
    last_delivery_at: datetime | None

    @property
    def should_pause(self) -> bool:
        return self.ignored_streak >= PAUSE_AFTER_IGNORED

    @property
    def min_gap_days(self) -> int:
        if self.should_pause:
            return _GAP_DAYS_BY_STREAK[-1]
        return _GAP_DAYS_BY_STREAK[self.ignored_streak]


def new_delivery_token() -> str:
    return secrets.token_urlsafe(16)


def backoff_state(
    db: Session,
    schedule: UserNotificationSchedule,
    *,
    now: datetime,
) -> BackoffState:
    query = select(NotificationDelivery).where(NotificationDelivery.schedule_id == schedule.id)
    if schedule.backoff_reset_at is not None:
        query = query.where(NotificationDelivery.sent_at > schedule.backoff_reset_at)
    query = query.order_by(NotificationDelivery.sent_at.desc()).limit(PAUSE_AFTER_IGNORED)
    deliveries = list(db.scalars(query).all())
    if not deliveries:
        return BackoffState(ignored_streak=0, last_delivery_at=None)

    streak = 0
    window_end = now
    for delivery in deliveries:
        if delivery.engaged_at is None:
            entry_at = _first_entry_between(
                db,
                user_id=delivery.user_id,
                start=delivery.sent_at,
                end=window_end,
            )
            if entry_at is not None:
                delivery.engaged_at = entry_at
        if delivery.engaged_at is not None:
            break
        streak += 1
        window_end = delivery.sent_at
    return BackoffState(ignored_streak=streak, last_delivery_at=deliveries[0].sent_at)


def record_delivery(
    db: Session,
    *,
    schedule: UserNotificationSchedule,
    channels: list[str],
    token: str,
    at: datetime,
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        user_id=schedule.user_id,
        schedule_id=schedule.id,
        kind=schedule.kind,
        channels=channels,
        token=token,
        sent_at=at,
    )
    db.add(delivery)
    return delivery


def mark_engaged(db: Session, *, token: str, at: datetime | None = None) -> bool:
    """Record a click on a reminder link. Unknown tokens are ignored."""
    instant = at if at is not None else datetime.now(UTC)
    result = db.execute(
        update(NotificationDelivery)
        .where(NotificationDelivery.token == token, NotificationDelivery.engaged_at.is_(None))
        .values(engaged_at=instant)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return bool(getattr(result, "rowcount", 0))


def pause_schedule(schedule: UserNotificationSchedule, *, at: datetime) -> None:
    schedule.paused_at = at


def resume_schedule(schedule: UserNotificationSchedule, *, at: datetime) -> None:
    schedule.paused_at = None
    schedule.backoff_reset_at = at


def _first_entry_between(
    db: Session,
    *,
    user_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> datetime | None:
    return db.scalar(
        select(MoodEntry.created_at)
        .where(
            MoodEntry.user_id == user_id,
            MoodEntry.created_at >= start,
            MoodEntry.created_at < end,
        )
        .order_by(MoodEntry.created_at)
        .limit(1)
    )
