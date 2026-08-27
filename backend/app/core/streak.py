"""Current consecutive-day streak for mood check-ins."""

from collections.abc import Iterable
from datetime import date, timedelta


def current_streak(dates: Iterable[date], *, today: date) -> int:
    """Count consecutive local days with at least one entry.

    The run must include today or yesterday. Missing today does not break the
    streak until the following midnight — same as common habit trackers.
    Future-dated entries are ignored.
    """
    logged = set(dates)
    if not logged:
        return 0
    start = today if today in logged else today - timedelta(days=1)
    if start not in logged:
        return 0
    run = 0
    day = start
    while day in logged:
        run += 1
        day -= timedelta(days=1)
    return run
