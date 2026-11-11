"""In-process memory of when the next reminder can become due.

cron-job.org calls the HTTP tick every 5 minutes. Before this cache every call read
the schedules from Neon, so the database never scaled to zero. Now a full pass also
works out the earliest moment any schedule could be due, and later ticks before that
moment answer ``idle`` without opening a database connection.

The tick goes back to the database when:

- the process has just started (empty cache);
- the cached moment has come;
- a schedule or a reminder-relevant user field changed (session events below);
- the snapshot is older than ``NOTIFICATIONS_DUE_CACHE_TTL_SECONDS``.

Limitation: the cache lives in one process. Production runs one Render instance with
one uvicorn process (``backend/Dockerfile`` starts uvicorn without ``--workers``), so
every change made through the API resets it. With several processes or instances a
change made in one would only reach the others after the TTL. The Docker Compose
worker (``python -m app.jobs.reminders``) is a separate process and does not use it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from itertools import chain
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import ORMExecuteState, Session

from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.notifications.reminders import parse_time_of_day

# Changing one of these can make a reminder sendable inside its current window
# (time zone, verified identity, a deliverable channel).
_USER_FIELDS_THAT_MATTER = (
    "timezone",
    "email",
    "email_verified_at",
    "telegram_user_id",
    "telegram_chat_id",
)
_STALE_KEY = "reminder_due_cache_stale"


@dataclass(frozen=True, slots=True)
class DueSnapshot:
    # None: no enabled schedule at all, so nothing is due until something changes.
    next_due_at: datetime | None
    computed_at: datetime


class DueCache:
    """Thread-safe holder for the latest snapshot (sync endpoints run in a threadpool)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: DueSnapshot | None = None
        self._generation = 0
        self._last_tick_at: datetime | None = None

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def snapshot(self) -> DueSnapshot | None:
        with self._lock:
            return self._snapshot

    @property
    def last_tick_at(self) -> datetime | None:
        """Last tick this process answered, idle or not (the "sender works" signal)."""
        with self._lock:
            return self._last_tick_at

    def note_tick(self, at: datetime) -> None:
        with self._lock:
            if self._last_tick_at is None or at > self._last_tick_at:
                self._last_tick_at = at

    def idle_snapshot(self, now: datetime, *, ttl: timedelta) -> DueSnapshot | None:
        """The snapshot that lets a tick at ``now`` skip the database, if there is one."""
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None or now - snapshot.computed_at >= ttl:
            return None
        if snapshot.next_due_at is not None and now >= snapshot.next_due_at:
            return None
        return snapshot

    def store(
        self, *, next_due_at: datetime | None, computed_at: datetime, generation: int
    ) -> bool:
        """Keep a snapshot unless something invalidated the cache after ``generation``."""
        with self._lock:
            if generation != self._generation:
                return False
            self._snapshot = DueSnapshot(next_due_at=next_due_at, computed_at=computed_at)
            return True

    def invalidate(self) -> None:
        with self._lock:
            self._generation += 1
            self._snapshot = None

    def reset(self) -> None:
        """Forget everything, as after a process restart (tests)."""
        with self._lock:
            self._generation += 1
            self._snapshot = None
            self._last_tick_at = None


reminder_due_cache = DueCache()


def next_reminder_at(
    *,
    after: datetime,
    time_of_day: time,
    tz: ZoneInfo,
    days_of_week: list[int] | None,
    interval_days: int,
    last_sent_at: datetime | None,
) -> datetime | None:
    """First start of a reminder window strictly after ``after``, in UTC.

    Mirrors ``process_due_reminders``: the window opens at ``time_of_day`` local time
    on an allowed weekday at least ``interval_days`` after the last send. Backoff for
    ignored reminders is left out on purpose: it only makes a pass skip the schedule,
    which costs one database visit, while a moment that is too late would lose a reminder.
    """
    local_today = after.astimezone(tz).date()
    last_sent_day = None if last_sent_at is None else _as_utc(last_sent_at).astimezone(tz).date()
    weekdays = set(days_of_week or [])
    for offset in range(max(interval_days, 1) + 8):
        day = local_today + timedelta(days=offset)
        if weekdays and day.weekday() not in weekdays:
            continue
        if last_sent_day is not None and (day - last_sent_day).days < interval_days:
            continue
        for start in _window_starts(day, time_of_day, tz):
            if start > after:
                return start
    return None


def compute_next_due_at(db: Session, *, after: datetime) -> datetime | None:
    """Earliest ``next_reminder_at`` over all enabled, unpaused schedules (one query)."""
    rows = db.execute(
        select(
            UserNotificationSchedule.time_of_day,
            UserNotificationSchedule.days_of_week,
            UserNotificationSchedule.interval_days,
            UserNotificationSchedule.last_sent_at,
            User.timezone,
        )
        .join(User, User.id == UserNotificationSchedule.user_id)
        .where(
            UserNotificationSchedule.enabled.is_(True),
            UserNotificationSchedule.paused_at.is_(None),
        )
    ).all()
    earliest: datetime | None = None
    for time_of_day, days_of_week, interval_days, last_sent_at, timezone_name in rows:
        try:
            tz = ZoneInfo(timezone_name)
            clock = parse_time_of_day(time_of_day)
        except (ZoneInfoNotFoundError, ValueError):
            # Never sendable; the full pass already reports it as an error.
            continue
        candidate = next_reminder_at(
            after=after,
            time_of_day=clock,
            tz=tz,
            days_of_week=days_of_week,
            interval_days=interval_days,
            last_sent_at=last_sent_at,
        )
        if candidate is not None and (earliest is None or candidate < earliest):
            earliest = candidate
    return earliest


def _window_starts(day: date, clock: time, tz: ZoneInfo) -> list[datetime]:
    """Both readings of a local wall time (they differ only around DST switches)."""
    naive = datetime.combine(day, clock)
    return sorted({naive.replace(tzinfo=tz, fold=fold).astimezone(UTC) for fold in (0, 1)})


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


# Invalidation: one place for every writer. A session that changes a schedule or a
# reminder-relevant user field resets the cache after its commit, so a new service
# that edits schedules needs no extra call. The tick's own writes (claims, pauses)
# reset it too, which is harmless: the tick reads the generation after its pass.


def _touches_reminders(session: Session) -> bool:
    for obj in chain(session.new, session.deleted):
        if isinstance(obj, UserNotificationSchedule):
            return True
    for obj in session.dirty:
        if isinstance(obj, UserNotificationSchedule) and session.is_modified(obj):
            return True
        if isinstance(obj, User):
            attrs = inspect(obj).attrs
            if any(attrs[name].history.has_changes() for name in _USER_FIELDS_THAT_MATTER):
                return True
    return False


@event.listens_for(Session, "after_flush")
def _note_flushed_changes(session: Session, _flush_context: object) -> None:
    if _touches_reminders(session):
        session.info[_STALE_KEY] = True


@event.listens_for(Session, "do_orm_execute")
def _note_bulk_changes(state: ORMExecuteState) -> None:
    if not (state.is_update or state.is_delete):
        return
    mapper = state.bind_mapper
    if mapper is not None and mapper.class_ in (UserNotificationSchedule, User):
        state.session.info[_STALE_KEY] = True


@event.listens_for(Session, "after_commit")
def _invalidate_after_commit(session: Session) -> None:
    if session.info.pop(_STALE_KEY, False):
        reminder_due_cache.invalidate()


@event.listens_for(Session, "after_rollback")
def _forget_rolled_back(session: Session) -> None:
    session.info.pop(_STALE_KEY, None)
