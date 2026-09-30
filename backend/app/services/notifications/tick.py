"""One reminder pass: heartbeat, flag checks, then send due reminders.

Shared by the long-lived worker (``python -m app.jobs.reminders``) and the
HTTP tick endpoint that an external scheduler (cron-job.org) calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.config import settings
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.reminders import ReminderRunStats, process_due_reminders
from app.services.notifications.worker_status import record_heartbeat

logger = logging.getLogger(__name__)


class ReminderTickOutcome(StrEnum):
    DONE = "done"
    WORKER_DISABLED = "worker_disabled"
    FEATURE_DISABLED = "feature_disabled"


@dataclass(slots=True)
class ReminderTickResult:
    outcome: ReminderTickOutcome
    stats: ReminderRunStats


def run_reminder_tick(
    db: Session,
    dispatcher: NotificationDispatcher,
    *,
    now: datetime | None = None,
) -> ReminderTickResult:
    record_heartbeat(db, meta={"phase": "tick"}, at=now)

    if not settings.notifications_worker_enabled:
        logger.warning("NOTIFICATIONS_WORKER_ENABLED=false — worker idle until enabled")
        return ReminderTickResult(ReminderTickOutcome.WORKER_DISABLED, ReminderRunStats())
    if not settings.feature_notifications_enabled:
        logger.info("FEATURE_NOTIFICATIONS_ENABLED=false — sleeping without scanning users")
        return ReminderTickResult(ReminderTickOutcome.FEATURE_DISABLED, ReminderRunStats())

    stats = process_due_reminders(db, dispatcher, now=now)
    record_heartbeat(
        db,
        meta={
            "phase": "done",
            "users_considered": stats.users_considered,
            "daily_mood_sent": stats.daily_mood_sent,
            "goal_reminders_sent": stats.goal_reminders_sent,
            "skipped": stats.skipped,
            "errors": len(stats.errors),
        },
        at=now,
    )
    logger.info(
        "reminders done: considered=%s daily=%s goals=%s skipped=%s errors=%s",
        stats.users_considered,
        stats.daily_mood_sent,
        stats.goal_reminders_sent,
        stats.skipped,
        len(stats.errors),
    )
    for error in stats.errors:
        logger.warning("reminder error: %s", error)
    return ReminderTickResult(ReminderTickOutcome.DONE, stats)
