"""Achievement criteria evaluators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.achievements import CriteriaType
from app.models.mood_entry import MoodEntry
from app.models.user import User


@dataclass(frozen=True, slots=True)
class CriteriaProgress:
    current: int
    target: int

    @property
    def complete(self) -> bool:
        return self.current >= self.target


def _resolve_tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _local_date(recorded_at: datetime, tz: ZoneInfo) -> date:
    instant = recorded_at if recorded_at.tzinfo is not None else recorded_at.replace(tzinfo=UTC)
    return instant.astimezone(tz).date()


def _entry_count(db: Session, *, user_id) -> int:
    return int(
        db.scalar(select(func.count()).select_from(MoodEntry).where(MoodEntry.user_id == user_id))
        or 0
    )


def _distinct_local_dates(db: Session, *, user: User) -> list[date]:
    tz = _resolve_tz(user.timezone)
    recorded = db.scalars(
        select(MoodEntry.recorded_at).where(MoodEntry.user_id == user.id)
    ).all()
    return sorted({_local_date(instant, tz) for instant in recorded})


def _longest_streak(dates: list[date]) -> int:
    if not dates:
        return 0
    best = 1
    run = 1
    for prev, curr in zip(dates, dates[1:], strict=False):
        if curr == prev + timedelta(days=1):
            run += 1
            best = max(best, run)
        elif curr != prev:
            run = 1
    return best


def _calendar_match(
    dates: list[date],
    *,
    weekday: int | None,
    month: int | None,
    day: int | None,
) -> bool:
    for d in dates:
        if weekday is not None and d.weekday() != weekday:
            continue
        if month is not None and d.month != month:
            continue
        if day is not None and d.day != day:
            continue
        return True
    return False


def evaluate_criteria(db: Session, *, user: User, criteria: dict) -> CriteriaProgress:
    criteria_type = criteria.get("type")
    if criteria_type == CriteriaType.ENTRY_COUNT.value:
        target = max(1, int(criteria.get("count", 1)))
        current = _entry_count(db, user_id=user.id)
        return CriteriaProgress(current=min(current, target), target=target)

    if criteria_type == CriteriaType.CONSECUTIVE_DAYS.value:
        target = max(1, int(criteria.get("days", 1)))
        streak = _longest_streak(_distinct_local_dates(db, user=user))
        return CriteriaProgress(current=min(streak, target), target=target)

    if criteria_type == CriteriaType.CALENDAR_MATCH.value:
        weekday = criteria.get("weekday")
        month = criteria.get("month")
        day = criteria.get("day")
        matched = _calendar_match(
            _distinct_local_dates(db, user=user),
            weekday=int(weekday) if weekday is not None else None,
            month=int(month) if month is not None else None,
            day=int(day) if day is not None else None,
        )
        return CriteriaProgress(current=1 if matched else 0, target=1)

    return CriteriaProgress(current=0, target=1)


def progress_target_for_criteria(criteria: dict) -> int:
    criteria_type = criteria.get("type")
    if criteria_type == CriteriaType.ENTRY_COUNT.value:
        return max(1, int(criteria.get("count", 1)))
    if criteria_type == CriteriaType.CONSECUTIVE_DAYS.value:
        return max(1, int(criteria.get("days", 1)))
    return 1
