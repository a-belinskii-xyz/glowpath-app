"""One reminder pass: flag checks, then send due reminders and record a heartbeat.

Shared by the long-lived worker (``python -m app.jobs.reminders``) and the
HTTP tick endpoint that an external scheduler (cron-job.org) calls. The endpoint
passes a ``DueCache`` so that ticks before the next due reminder skip the database
(see ``due_cache.py``); the worker runs a full pass every time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.orm import Session

from app.config import settings
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.due_cache import DueCache, compute_next_due_at
from app.services.notifications.reminders import ReminderRunStats, process_due_reminders
from app.services.notifications.worker_status import record_heartbeat

logger = logging.getLogger(__name__)


class ReminderTickOutcome(StrEnum):
    DONE = "done"
    # Nothing can be due yet: answered from memory, no database access.
    IDLE = "idle"
    WORKER_DISABLED = "worker_disabled"
    FEATURE_DISABLED = "feature_disabled"


@dataclass(slots=True)
class ReminderTickResult:
    outcome: ReminderTickOutcome
    stats: ReminderRunStats
    # When the next pass is needed; only known with a due cache.
    next_due_at: datetime | None = None


def run_reminder_tick(
    db: Session,
    dispatcher: NotificationDispatcher,
    *,
    now: datetime | None = None,
    due_cache: DueCache | None = None,
) -> ReminderTickResult:
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)

    if not settings.notifications_worker_enabled:
        logger.warning("NOTIFICATIONS_WORKER_ENABLED=false — worker idle until enabled")
        return ReminderTickResult(ReminderTickOutcome.WORKER_DISABLED, ReminderRunStats())
    if not settings.feature_notifications_enabled:
        logger.info("FEATURE_NOTIFICATIONS_ENABLED=false — sleeping without scanning users")
        return ReminderTickResult(ReminderTickOutcome.FEATURE_DISABLED, ReminderRunStats())

    if due_cache is not None:
        due_cache.note_tick(instant)
        ttl = timedelta(seconds=settings.notifications_due_cache_ttl_seconds)
        snapshot = due_cache.idle_snapshot(instant, ttl=ttl)
        if snapshot is not None:
            return ReminderTickResult(
                ReminderTickOutcome.IDLE,
                ReminderRunStats(),
                next_due_at=snapshot.next_due_at,
            )

    record_heartbeat(db, meta={"phase": "tick"}, at=instant)
    stats = process_due_reminders(db, dispatcher, now=instant)
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
        at=instant,
    )
    next_due_at = None
    if due_cache is not None:
        next_due_at = _refresh_due_cache(db, due_cache, stats=stats, after=instant)
    logger.info(
        "reminders done: considered=%s daily=%s goals=%s skipped=%s errors=%s next_due=%s",
        stats.users_considered,
        stats.daily_mood_sent,
        stats.goal_reminders_sent,
        stats.skipped,
        len(stats.errors),
        next_due_at.isoformat() if next_due_at is not None else "-",
    )
    for error in stats.errors:
        logger.warning("reminder error: %s", error)
    return ReminderTickResult(ReminderTickOutcome.DONE, stats, next_due_at=next_due_at)


def _refresh_due_cache(
    db: Session,
    due_cache: DueCache,
    *,
    stats: ReminderRunStats,
    after: datetime,
) -> datetime | None:
    # Read before the query: a change committed after this point bumps the
    # generation and the snapshot below is dropped instead of hiding it.
    generation = due_cache.generation
    if stats.released_claims:
        # A delivery failed and gave its claim back: retry on the next tick.
        next_due_at: datetime | None = after
    else:
        # Every window open at ``after`` was handled by this pass, so the next
        # moment of interest is the first window that opens later.
        next_due_at = compute_next_due_at(db, after=after)
    due_cache.store(next_due_at=next_due_at, computed_at=after, generation=generation)
    return next_due_at
