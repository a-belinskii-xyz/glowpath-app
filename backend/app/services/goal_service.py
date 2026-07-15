from __future__ import annotations

import re
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.user import User

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


class GoalError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def list_goals(db: Session, *, user_id: uuid.UUID) -> list[Goal]:
    return list(
        db.scalars(
            select(Goal).where(Goal.user_id == user_id).order_by(Goal.sort_order, Goal.slug)
        ).all()
    )


def get_goal(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    if goal is None:
        raise GoalError("Goal not found", status_code=404)
    return goal


def create_goal(
    db: Session,
    *,
    user_id: uuid.UUID,
    labels: dict[str, str],
    times_per_week: int,
    starts_on: date,
    slug: str | None = None,
    sort_order: int | None = None,
    show_on_entry: bool = False,
) -> Goal:
    if show_on_entry:
        _ensure_visible_slot_available(db, user_id=user_id)
    resolved_slug = slug or _unique_goal_slug(db, user_id=user_id, base=_slugify(labels))
    resolved_order = (
        sort_order
        if sort_order is not None
        else _next_sort_order(
            db,
            select(func.max(Goal.sort_order)).where(Goal.user_id == user_id),
        )
    )
    goal = Goal(
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        times_per_week=times_per_week,
        starts_on=starts_on,
        sort_order=resolved_order,
        show_on_entry=show_on_entry,
    )
    db.add(goal)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GoalError("Goal slug already exists", status_code=409) from exc
    return get_goal(db, user_id=user_id, goal_id=goal.id)


def patch_goal(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    slug: str | None = None,
    labels: dict[str, str] | None = None,
    times_per_week: int | None = None,
    starts_on: date | None = None,
    sort_order: int | None = None,
    show_on_entry: bool | None = None,
) -> Goal:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    if slug is not None:
        goal.slug = slug
    if labels is not None:
        goal.labels = labels
    if times_per_week is not None:
        goal.times_per_week = times_per_week
    if starts_on is not None:
        goal.starts_on = starts_on
    if sort_order is not None:
        goal.sort_order = sort_order
    if show_on_entry is not None and show_on_entry != goal.show_on_entry:
        if show_on_entry:
            _ensure_visible_slot_available(db, user_id=user_id)
        goal.show_on_entry = show_on_entry
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GoalError("Goal slug already exists", status_code=409) from exc
    return get_goal(db, user_id=user_id, goal_id=goal_id)


def delete_goal(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    if _goal_is_linked(db, goal_id=goal.id):
        raise GoalError(
            "Cannot delete goal while it is used by mood entries",
            status_code=409,
        )
    db.delete(goal)
    db.commit()


def reorder_goals(
    db: Session,
    *,
    user_id: uuid.UUID,
    ordered_ids: list[uuid.UUID],
) -> list[Goal]:
    goals = list_goals(db, user_id=user_id)
    by_id = {goal.id: goal for goal in goals}
    if set(ordered_ids) != set(by_id):
        raise GoalError("ordered_ids must include every goal exactly once", status_code=400)
    for index, goal_id in enumerate(ordered_ids):
        by_id[goal_id].sort_order = index
    db.commit()
    return list_goals(db, user_id=user_id)


def week_completion_counts(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    goal_ids: list[uuid.UUID] | None = None,
    reference_date: date | None = None,
) -> dict[uuid.UUID, int]:
    """Count distinct local days each goal was completed in the current ISO week."""
    if goal_ids is not None and not goal_ids:
        return {}

    tz = _resolve_user_tz(timezone_name)
    today = reference_date if reference_date is not None else datetime.now(tz).date()
    week_start, week_end = _iso_week_bounds(today)
    range_start_utc = datetime(
        week_start.year, week_start.month, week_start.day, tzinfo=tz
    ).astimezone(UTC)
    range_end_utc = datetime(week_end.year, week_end.month, week_end.day, tzinfo=tz).astimezone(UTC)

    stmt = (
        select(MoodEntryGoal.goal_id, MoodEntry.recorded_at)
        .join(MoodEntry, MoodEntry.id == MoodEntryGoal.mood_entry_id)
        .where(
            MoodEntry.user_id == user_id,
            MoodEntry.recorded_at >= range_start_utc,
            MoodEntry.recorded_at < range_end_utc,
        )
    )
    if goal_ids is not None:
        stmt = stmt.where(MoodEntryGoal.goal_id.in_(goal_ids))

    days_by_goal: dict[uuid.UUID, set[date]] = defaultdict(set)
    for goal_id, recorded_at in db.execute(stmt).all():
        local_day = recorded_at.astimezone(tz).date()
        if week_start <= local_day < week_end:
            days_by_goal[goal_id].add(local_day)

    ids = goal_ids if goal_ids is not None else list(days_by_goal)
    return {goal_id: len(days_by_goal.get(goal_id, set())) for goal_id in ids}


def serialize_goal(
    goal: Goal,
    *,
    locale: str,
    completed_this_week: int = 0,
) -> dict[str, Any]:
    return {
        "id": goal.id,
        "slug": goal.slug,
        "label": resolve_label(goal.labels, locale),
        "labels": goal.labels,
        "times_per_week": goal.times_per_week,
        "starts_on": goal.starts_on,
        "sort_order": goal.sort_order,
        "show_on_entry": goal.show_on_entry,
        "completed_this_week": completed_this_week,
    }


def serialize_goals(
    goals: list[Goal],
    *,
    locale: str,
    completed_by_goal: dict[uuid.UUID, int] | None = None,
) -> list[dict[str, Any]]:
    counts = completed_by_goal or {}
    return [
        serialize_goal(goal, locale=locale, completed_this_week=counts.get(goal.id, 0))
        for goal in goals
    ]


def load_goals_week_stats(
    db: Session,
    *,
    user: User,
    goals: list[Goal],
) -> dict[uuid.UUID, int]:
    return week_completion_counts(
        db,
        user_id=user.id,
        timezone_name=user.timezone,
        goal_ids=[goal.id for goal in goals],
    )


def _resolve_user_tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise GoalError(f"Unknown timezone: {timezone_name}", status_code=400) from exc


def _iso_week_bounds(day: date) -> tuple[date, date]:
    week_start = day - timedelta(days=day.weekday())
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def _count_visible_goals(db: Session, *, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(Goal)
        .where(Goal.user_id == user_id, Goal.show_on_entry.is_(True))
    )
    return int(count or 0)


def _ensure_visible_slot_available(db: Session, *, user_id: uuid.UUID) -> None:
    limit = settings.entry_visible_goal_limit
    if _count_visible_goals(db, user_id=user_id) >= limit:
        raise GoalError(
            f"You can show at most {limit} goals on the entry form",
            status_code=400,
        )


def _goal_is_linked(db: Session, *, goal_id: uuid.UUID) -> bool:
    count = db.scalar(
        select(func.count()).select_from(MoodEntryGoal).where(MoodEntryGoal.goal_id == goal_id)
    )
    return bool(count)


def _next_sort_order(db: Session, query: Select[Any]) -> int:
    current = db.scalar(query)
    return 0 if current is None else int(current) + 1


def _slugify(labels: dict[str, str]) -> str:
    raw = labels.get(DEFAULT_LOCALE) or next(iter(labels.values()))
    slug = _SLUGIFY_RE.sub("_", raw.lower()).strip("_")
    if not slug:
        slug = "item"
    if not slug[0].isalpha():
        slug = f"g_{slug}"
    return slug[:64]


def _unique_goal_slug(db: Session, *, user_id: uuid.UUID, base: str) -> str:
    return _unique_slug(
        base,
        exists=lambda candidate: (
            db.scalar(
                select(Goal.id).where(
                    Goal.user_id == user_id,
                    Goal.slug == candidate,
                )
            )
            is not None
        ),
    )


def _unique_slug(base: str, *, exists: Callable[[str], bool]) -> str:
    candidate = base
    index = 2
    while exists(candidate):
        suffix = f"_{index}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        index += 1
    return candidate
