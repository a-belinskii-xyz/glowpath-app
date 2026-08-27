"""Same-day check-in streak for mood entries."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo


def local_date(instant: datetime, tz: ZoneInfo) -> date:
    value = instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)
    return value.astimezone(tz).date()


def check_in_date(
    recorded_at: datetime,
    written_at: datetime,
    *,
    tz: ZoneInfo,
) -> date | None:
    """Return the civil day this entry counts for, or None if it was backdated.

    An entry counts only when it was written on the same local calendar day it
    claims to record — in the timezone the user had at write time.
    """
    recorded_day = local_date(recorded_at, tz)
    written_day = local_date(written_at, tz)
    if recorded_day != written_day:
        return None
    return recorded_day


def current_streak(dates: Iterable[date], *, today: date) -> int:
    """Count consecutive check-in days that are still alive.

    The run must touch today, yesterday, or tomorrow. Tomorrow covers a
    westward timezone change that moves the clock back one civil day.
    Dates more than one day in the future are ignored as the live anchor.
    """
    logged = set(dates)
    if not logged:
        return 0
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)
    if tomorrow in logged:
        start = tomorrow
    elif today in logged:
        start = today
    elif yesterday in logged:
        start = yesterday
    else:
        return 0
    run = 0
    day = start
    while day in logged:
        run += 1
        day -= timedelta(days=1)
    return run
