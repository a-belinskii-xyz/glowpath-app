"""Achievement criteria evaluators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.achievements import CriteriaType
from app.core.attachment_kind import AttachmentKind
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MoodEntryAttachment
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
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


def _aware(recorded_at: datetime) -> datetime:
    return recorded_at if recorded_at.tzinfo is not None else recorded_at.replace(tzinfo=UTC)


def _local_date(recorded_at: datetime, tz: ZoneInfo) -> date:
    return _aware(recorded_at).astimezone(tz).date()


def _local_hour(recorded_at: datetime, tz: ZoneInfo) -> int:
    return _aware(recorded_at).astimezone(tz).hour


def _count(value: int | None) -> int:
    return int(value or 0)


def _target_count(criteria: dict, key: str = "count") -> int:
    return max(1, int(criteria.get(key, 1)))


def _progress(current: int, target: int) -> CriteriaProgress:
    return CriteriaProgress(current=min(current, target), target=target)


def _entry_count(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(select(func.count()).select_from(MoodEntry).where(MoodEntry.user_id == user_id))
    )


def _distinct_local_dates(db: Session, *, user: User) -> list[date]:
    tz = _resolve_tz(user.timezone)
    recorded = db.scalars(select(MoodEntry.recorded_at).where(MoodEntry.user_id == user.id)).all()
    return sorted({_local_date(instant, tz) for instant in recorded})


def _distinct_check_in_dates(db: Session, *, user: User) -> list[date]:
    dates = db.scalars(
        select(MoodEntry.logged_on).where(
            MoodEntry.user_id == user.id,
            MoodEntry.logged_on.is_not(None),
        )
    ).all()
    return sorted({day for day in dates if day is not None})


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


def _hour_in_range(hour: int, hour_from: int, hour_to: int) -> bool:
    if hour_from < hour_to:
        return hour_from <= hour < hour_to
    if hour_from > hour_to:
        return hour >= hour_from or hour < hour_to
    return False


def _entries_with_note(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count())
            .select_from(MoodEntry)
            .where(
                MoodEntry.user_id == user_id,
                MoodEntry.note.is_not(None),
                func.length(func.trim(MoodEntry.note)) > 0,
            )
        )
    )


def _favorite_count(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count())
            .select_from(MoodEntry)
            .where(MoodEntry.user_id == user_id, MoodEntry.is_favorite.is_(True))
        )
    )


def _score_count(db: Session, *, user_id: UUID, score: int) -> int:
    return _count(
        db.scalar(
            select(func.count())
            .select_from(MoodEntry)
            .where(MoodEntry.user_id == user_id, MoodEntry.score == score)
        )
    )


def _distinct_scores(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count(func.distinct(MoodEntry.score))).where(MoodEntry.user_id == user_id)
        )
    )


def _attachment_count(db: Session, *, user_id: UUID, kind: str | None) -> int:
    stmt = (
        select(func.count())
        .select_from(MoodEntryAttachment)
        .join(MoodEntry, MoodEntry.id == MoodEntryAttachment.mood_entry_id)
        .where(MoodEntry.user_id == user_id)
    )
    if kind:
        try:
            attachment_kind = AttachmentKind(kind)
        except ValueError:
            return 0
        stmt = stmt.where(MoodEntryAttachment.kind == attachment_kind)
    return _count(db.scalar(stmt))


def _tagged_entry_count(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count(func.distinct(MoodEntryTag.mood_entry_id)))
            .select_from(MoodEntryTag)
            .join(MoodEntry, MoodEntry.id == MoodEntryTag.mood_entry_id)
            .where(MoodEntry.user_id == user_id)
        )
    )


def _distinct_tags_used(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count(func.distinct(MoodEntryTag.tag_id)))
            .select_from(MoodEntryTag)
            .join(MoodEntry, MoodEntry.id == MoodEntryTag.mood_entry_id)
            .where(MoodEntry.user_id == user_id)
        )
    )


def _goal_created_count(db: Session, *, user: User) -> int:
    """Count goals the user created themselves, not the onboarding defaults."""
    return _count(
        db.scalar(
            select(func.count())
            .select_from(Goal)
            .where(Goal.user_id == user.id, Goal.created_at > user.created_at)
        )
    )


def _goal_checkin_count(db: Session, *, user_id: UUID) -> int:
    return _count(
        db.scalar(
            select(func.count())
            .select_from(MoodEntryGoal)
            .join(MoodEntry, MoodEntry.id == MoodEntryGoal.mood_entry_id)
            .where(MoodEntry.user_id == user_id)
        )
    )


def _source_prefix_count(db: Session, *, user_id: UUID, prefix: str) -> int:
    cleaned = prefix.strip().lower()
    if not cleaned:
        return 0
    like = f"{cleaned}:%"
    return _count(
        db.scalar(
            select(func.count())
            .select_from(MoodEntry)
            .where(
                MoodEntry.user_id == user_id,
                MoodEntry.source.is_not(None),
                MoodEntry.source.ilike(like),
            )
        )
    )


def _local_hour_range_count(
    db: Session,
    *,
    user: User,
    hour_from: int,
    hour_to: int,
) -> int:
    tz = _resolve_tz(user.timezone)
    recorded = db.scalars(select(MoodEntry.recorded_at).where(MoodEntry.user_id == user.id)).all()
    return sum(
        1 for instant in recorded if _hour_in_range(_local_hour(instant, tz), hour_from, hour_to)
    )


def evaluate_criteria(db: Session, *, user: User, criteria: dict) -> CriteriaProgress:
    criteria_type = criteria.get("type")
    if criteria_type == CriteriaType.ENTRY_COUNT.value:
        target = _target_count(criteria)
        return _progress(_entry_count(db, user_id=user.id), target)

    if criteria_type == CriteriaType.CONSECUTIVE_DAYS.value:
        target = _target_count(criteria, "days")
        streak = _longest_streak(_distinct_check_in_dates(db, user=user))
        return _progress(streak, target)

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

    if criteria_type == CriteriaType.ENTRIES_WITH_NOTE.value:
        target = _target_count(criteria)
        return _progress(_entries_with_note(db, user_id=user.id), target)

    if criteria_type == CriteriaType.FAVORITE_COUNT.value:
        target = _target_count(criteria)
        return _progress(_favorite_count(db, user_id=user.id), target)

    if criteria_type == CriteriaType.SCORE_COUNT.value:
        target = _target_count(criteria)
        score = int(criteria.get("score", 0))
        return _progress(_score_count(db, user_id=user.id, score=score), target)

    if criteria_type == CriteriaType.DISTINCT_SCORES.value:
        target = _target_count(criteria)
        return _progress(_distinct_scores(db, user_id=user.id), target)

    if criteria_type == CriteriaType.ATTACHMENT_COUNT.value:
        target = _target_count(criteria)
        kind = criteria.get("kind")
        return _progress(
            _attachment_count(db, user_id=user.id, kind=str(kind) if kind else None),
            target,
        )

    if criteria_type == CriteriaType.TAGGED_ENTRY_COUNT.value:
        target = _target_count(criteria)
        return _progress(_tagged_entry_count(db, user_id=user.id), target)

    if criteria_type == CriteriaType.DISTINCT_TAGS_USED.value:
        target = _target_count(criteria)
        return _progress(_distinct_tags_used(db, user_id=user.id), target)

    if criteria_type == CriteriaType.GOAL_CREATED_COUNT.value:
        target = _target_count(criteria)
        return _progress(_goal_created_count(db, user=user), target)

    if criteria_type == CriteriaType.GOAL_CHECKIN_COUNT.value:
        target = _target_count(criteria)
        return _progress(_goal_checkin_count(db, user_id=user.id), target)

    if criteria_type == CriteriaType.SOURCE_PREFIX.value:
        target = _target_count(criteria)
        prefix = str(criteria.get("prefix") or "")
        return _progress(_source_prefix_count(db, user_id=user.id, prefix=prefix), target)

    if criteria_type == CriteriaType.LOCAL_HOUR_RANGE.value:
        target = _target_count(criteria)
        hour_from = int(criteria.get("hour_from", 0))
        hour_to = int(criteria.get("hour_to", 0))
        return _progress(
            _local_hour_range_count(db, user=user, hour_from=hour_from, hour_to=hour_to),
            target,
        )

    if criteria_type == CriteriaType.DISTINCT_CHECKIN_DAYS.value:
        target = _target_count(criteria)
        return _progress(len(_distinct_check_in_dates(db, user=user)), target)

    return CriteriaProgress(current=0, target=1)


def progress_target_for_criteria(criteria: dict) -> int:
    criteria_type = criteria.get("type")
    if criteria_type == CriteriaType.CONSECUTIVE_DAYS.value:
        return _target_count(criteria, "days")
    if criteria_type == CriteriaType.CALENDAR_MATCH.value:
        return 1
    if criteria_type in CRITERIA_TYPES_WITH_COUNT:
        return _target_count(criteria)
    return 1


CRITERIA_TYPES_WITH_COUNT = frozenset(
    {
        CriteriaType.ENTRY_COUNT.value,
        CriteriaType.ENTRIES_WITH_NOTE.value,
        CriteriaType.FAVORITE_COUNT.value,
        CriteriaType.SCORE_COUNT.value,
        CriteriaType.DISTINCT_SCORES.value,
        CriteriaType.ATTACHMENT_COUNT.value,
        CriteriaType.TAGGED_ENTRY_COUNT.value,
        CriteriaType.DISTINCT_TAGS_USED.value,
        CriteriaType.GOAL_CREATED_COUNT.value,
        CriteriaType.GOAL_CHECKIN_COUNT.value,
        CriteriaType.SOURCE_PREFIX.value,
        CriteriaType.LOCAL_HOUR_RANGE.value,
        CriteriaType.DISTINCT_CHECKIN_DAYS.value,
    }
)
