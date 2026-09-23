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
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.goal_tracking import MAX_GOAL_AMOUNT, MAX_GOAL_UNIT_LENGTH, GoalTrackingKind
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.core.mood_builtin_icons import is_valid_builtin_icon_slug
from app.core.mood_scale import MoodScoreIconType, is_valid_hex_color
from app.models.goal import (
    DEFAULT_GOAL_COLOR,
    DEFAULT_GOAL_ICON,
    DEFAULT_GOAL_ICON_TYPE,
    Goal,
)
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.user import User
from app.models.user_goal_icon import UserGoalIcon

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")
_MAX_EMOJI_LENGTH = 8


class GoalError(AppError):
    pass


def list_goals(db: Session, *, user_id: uuid.UUID) -> list[Goal]:
    return list(
        db.scalars(
            select(Goal).where(Goal.user_id == user_id).order_by(Goal.sort_order, Goal.slug)
        ).all()
    )


def get_goal(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    if goal is None:
        raise GoalError("Goal not found", code=ErrorCode.GOAL_NOT_FOUND, status_code=404)
    return goal


def create_goal(
    db: Session,
    *,
    user_id: uuid.UUID,
    labels: dict[str, str],
    times_per_week: int,
    starts_on: date,
    ends_on: date | None = None,
    slug: str | None = None,
    sort_order: int | None = None,
    show_on_entry: bool = False,
    show_in_stats: bool = False,
    color: str | None = None,
    icon_type: str | None = None,
    icon: str | None = None,
    tracking_kind: str | GoalTrackingKind = GoalTrackingKind.BINARY,
    target_amount: int | None = None,
    unit: str | None = None,
) -> Goal:
    if show_on_entry:
        _ensure_visible_slot_available(db, user_id=user_id)
    if show_in_stats:
        _ensure_stats_slot_available(db, user_id=user_id)
    _validate_goal_dates(starts_on=starts_on, ends_on=ends_on)
    kind, resolved_target, resolved_unit = _validate_tracking(
        tracking_kind=tracking_kind,
        target_amount=target_amount,
        unit=unit,
    )
    resolved_slug = slug or _unique_goal_slug(db, user_id=user_id, base=_slugify(labels))
    resolved_order = (
        sort_order
        if sort_order is not None
        else _next_sort_order(
            db,
            select(func.max(Goal.sort_order)).where(Goal.user_id == user_id),
        )
    )
    style = _validate_goal_style(
        db,
        user_id=user_id,
        goal_id=None,
        color=color if color is not None else DEFAULT_GOAL_COLOR,
        icon_type=icon_type if icon_type is not None else DEFAULT_GOAL_ICON_TYPE,
        icon=icon if icon is not None else DEFAULT_GOAL_ICON,
    )
    goal = Goal(
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        times_per_week=times_per_week,
        tracking_kind=kind.value,
        target_amount=resolved_target,
        unit=resolved_unit,
        starts_on=starts_on,
        ends_on=ends_on,
        sort_order=resolved_order,
        show_on_entry=show_on_entry,
        show_in_stats=show_in_stats,
        color=style["color"],
        icon_type=style["icon_type"],
        icon=style["icon"],
    )
    db.add(goal)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GoalError(
            "Goal slug already exists", code=ErrorCode.GOAL_SLUG_EXISTS, status_code=409
        ) from exc
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
    ends_on: date | None = None,
    ends_on_set: bool = False,
    sort_order: int | None = None,
    show_on_entry: bool | None = None,
    show_in_stats: bool | None = None,
    color: str | None = None,
    icon_type: str | None = None,
    icon: str | None = None,
    tracking_kind: str | GoalTrackingKind | None = None,
    target_amount: int | None = None,
    target_amount_set: bool = False,
    unit: str | None = None,
    unit_set: bool = False,
) -> Goal:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    if slug is not None:
        goal.slug = slug
    if labels is not None:
        goal.labels = labels
    if times_per_week is not None:
        goal.times_per_week = times_per_week
    next_kind = tracking_kind if tracking_kind is not None else goal.tracking_kind
    next_target = target_amount if target_amount_set else goal.target_amount
    next_unit = unit if unit_set else goal.unit
    if tracking_kind is not None or target_amount_set or unit_set:
        kind, resolved_target, resolved_unit = _validate_tracking(
            tracking_kind=next_kind,
            target_amount=next_target,
            unit=next_unit,
        )
        goal.tracking_kind = kind.value
        goal.target_amount = resolved_target
        goal.unit = resolved_unit
    if starts_on is not None:
        goal.starts_on = starts_on
    if ends_on_set:
        goal.ends_on = ends_on
    _validate_goal_dates(starts_on=goal.starts_on, ends_on=goal.ends_on)
    if sort_order is not None:
        goal.sort_order = sort_order
    if show_on_entry is not None and show_on_entry != goal.show_on_entry:
        if show_on_entry:
            _ensure_visible_slot_available(db, user_id=user_id)
        goal.show_on_entry = show_on_entry
    if show_in_stats is not None and show_in_stats != goal.show_in_stats:
        if show_in_stats:
            _ensure_stats_slot_available(db, user_id=user_id)
        goal.show_in_stats = show_in_stats
    if color is not None or icon_type is not None or icon is not None:
        style = _validate_goal_style(
            db,
            user_id=user_id,
            goal_id=goal.id,
            color=color if color is not None else goal.color,
            icon_type=icon_type if icon_type is not None else goal.icon_type,
            icon=icon if icon is not None else goal.icon,
        )
        goal.color = style["color"]
        goal.icon_type = style["icon_type"]
        goal.icon = style["icon"]
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GoalError(
            "Goal slug already exists", code=ErrorCode.GOAL_SLUG_EXISTS, status_code=409
        ) from exc
    return get_goal(db, user_id=user_id, goal_id=goal_id)


def delete_goal(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    if _goal_is_linked(db, goal_id=goal.id):
        raise GoalError(
            "Cannot delete goal while it is used by mood entries",
            code=ErrorCode.GOAL_IN_USE,
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
        raise GoalError(
            "ordered_ids must include every goal exactly once",
            code=ErrorCode.GOAL_REORDER_MISMATCH,
            status_code=400,
        )
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
    tz = _resolve_user_tz(timezone_name)
    today = reference_date if reference_date is not None else datetime.now(tz).date()
    week_start, week_end = _iso_week_bounds(today)
    progress = period_goal_progress(
        db,
        user_id=user_id,
        timezone_name=timezone_name,
        period_start=week_start,
        period_end=week_end,
        goal_ids=goal_ids,
    )
    return {goal_id: item.completed_days for goal_id, item in progress.items()}


def period_completion_counts(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    period_start: date,
    period_end: date,
    goal_ids: list[uuid.UUID] | None = None,
) -> dict[uuid.UUID, int]:
    """Count distinct local days each goal was completed in ``[period_start, period_end)``."""
    progress = period_goal_progress(
        db,
        user_id=user_id,
        timezone_name=timezone_name,
        period_start=period_start,
        period_end=period_end,
        goal_ids=goal_ids,
    )
    return {goal_id: item.completed_days for goal_id, item in progress.items()}


class GoalPeriodProgress:
    __slots__ = ("completed_days", "daily_amounts", "tracking_kind", "target_amount")

    def __init__(
        self,
        *,
        completed_days: int,
        daily_amounts: dict[date, int],
        tracking_kind: str,
        target_amount: int | None,
    ) -> None:
        self.completed_days = completed_days
        self.daily_amounts = daily_amounts
        self.tracking_kind = tracking_kind
        self.target_amount = target_amount

    @property
    def amount_in_period(self) -> int:
        return sum(self.daily_amounts.values())

    def amount_on(self, day: date) -> int:
        return self.daily_amounts.get(day, 0)


def period_goal_progress(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    period_start: date,
    period_end: date,
    goal_ids: list[uuid.UUID] | None = None,
) -> dict[uuid.UUID, GoalPeriodProgress]:
    """Per-goal daily amounts and completed-day counts in ``[period_start, period_end)``."""
    if period_end <= period_start:
        raise GoalError(
            "period_end must be after period_start", code=ErrorCode.PERIOD_END_BEFORE_START
        )
    if goal_ids is not None and not goal_ids:
        return {}

    tz = _resolve_user_tz(timezone_name)
    range_start_utc = datetime(
        period_start.year, period_start.month, period_start.day, tzinfo=tz
    ).astimezone(UTC)
    range_end_utc = datetime(
        period_end.year, period_end.month, period_end.day, tzinfo=tz
    ).astimezone(UTC)

    stmt = (
        select(
            MoodEntryGoal.goal_id,
            MoodEntry.recorded_at,
            MoodEntryGoal.amount,
            Goal.tracking_kind,
            Goal.target_amount,
        )
        .join(MoodEntry, MoodEntry.id == MoodEntryGoal.mood_entry_id)
        .join(Goal, Goal.id == MoodEntryGoal.goal_id)
        .where(
            MoodEntry.user_id == user_id,
            MoodEntry.recorded_at >= range_start_utc,
            MoodEntry.recorded_at < range_end_utc,
        )
    )
    if goal_ids is not None:
        stmt = stmt.where(MoodEntryGoal.goal_id.in_(goal_ids))

    daily: dict[uuid.UUID, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    meta: dict[uuid.UUID, tuple[str, int | None]] = {}
    for goal_id, recorded_at, amount, tracking_kind, target_amount in db.execute(stmt).all():
        local_day = recorded_at.astimezone(tz).date()
        if not (period_start <= local_day < period_end):
            continue
        meta[goal_id] = (tracking_kind, target_amount)
        if tracking_kind == GoalTrackingKind.QUANTITY:
            daily[goal_id][local_day] += int(amount or 0)
        else:
            daily[goal_id][local_day] = 1

    ids = goal_ids if goal_ids is not None else list({*daily, *meta})
    result: dict[uuid.UUID, GoalPeriodProgress] = {}
    for goal_id in ids:
        kind, target = meta.get(goal_id, (GoalTrackingKind.BINARY.value, None))
        amounts = dict(daily.get(goal_id, {}))
        if kind == GoalTrackingKind.QUANTITY:
            threshold = int(target or 0)
            completed = sum(1 for value in amounts.values() if value >= threshold)
        else:
            completed = len(amounts)
        result[goal_id] = GoalPeriodProgress(
            completed_days=completed,
            daily_amounts=amounts,
            tracking_kind=kind,
            target_amount=target,
        )
    return result


def period_target(*, times_per_week: int, period_days: int) -> int:
    if period_days <= 0:
        return times_per_week
    return max(1, round(times_per_week * period_days / 7))


def goal_is_active_on(goal: Goal, day: date) -> bool:
    if day < goal.starts_on:
        return False
    return goal.ends_on is None or day <= goal.ends_on


def serialize_goal(
    goal: Goal,
    *,
    locale: str,
    completed_this_week: int = 0,
    day_amount: int = 0,
) -> dict[str, Any]:
    return {
        "id": goal.id,
        "slug": goal.slug,
        "label": resolve_label(goal.labels, locale),
        "labels": goal.labels,
        "times_per_week": goal.times_per_week,
        "tracking_kind": goal.tracking_kind,
        "target_amount": goal.target_amount,
        "unit": goal.unit,
        "starts_on": goal.starts_on,
        "ends_on": goal.ends_on,
        "sort_order": goal.sort_order,
        "show_on_entry": goal.show_on_entry,
        "show_in_stats": goal.show_in_stats,
        "color": goal.color,
        "icon_type": goal.icon_type,
        "icon": goal.icon,
        "completed_this_week": completed_this_week,
        "day_amount": day_amount,
    }


def get_goal_stats(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    locale: str,
    recorded_from: datetime,
    recorded_to: datetime,
) -> dict[str, Any]:
    """Return per-goal completion stats for a recorded range in the user timezone."""
    tz = _resolve_user_tz(timezone_name)
    from_utc = _to_utc(recorded_from)
    to_utc = _to_utc(recorded_to)
    if to_utc <= from_utc:
        raise GoalError(
            "recorded_to must be after recorded_from", code=ErrorCode.RECORDED_TO_BEFORE_FROM
        )

    period_start = _local_date(from_utc, tz)
    period_end = _local_date(to_utc, tz)
    if period_end <= period_start:
        raise GoalError(
            "recorded_to must be after recorded_from", code=ErrorCode.RECORDED_TO_BEFORE_FROM
        )
    period_days = (period_end - period_start).days

    goals = [goal for goal in list_goals(db, user_id=user_id) if goal.show_in_stats]
    overlapping = [
        goal
        for goal in goals
        if goal.starts_on < period_end and (goal.ends_on is None or goal.ends_on >= period_start)
    ]
    progress = period_goal_progress(
        db,
        user_id=user_id,
        timezone_name=timezone_name,
        period_start=period_start,
        period_end=period_end,
        goal_ids=[goal.id for goal in overlapping],
    )
    items = [
        {
            "id": goal.id,
            "slug": goal.slug,
            "label": resolve_label(goal.labels, locale),
            "labels": goal.labels,
            "times_per_week": goal.times_per_week,
            "tracking_kind": goal.tracking_kind,
            "target_amount": goal.target_amount,
            "unit": goal.unit,
            "starts_on": goal.starts_on,
            "ends_on": goal.ends_on,
            "sort_order": goal.sort_order,
            "show_on_entry": goal.show_on_entry,
            "show_in_stats": goal.show_in_stats,
            "color": goal.color,
            "icon_type": goal.icon_type,
            "icon": goal.icon,
            "completed_in_period": progress[goal.id].completed_days,
            "period_target": period_target(
                times_per_week=goal.times_per_week,
                period_days=period_days,
            ),
            "amount_in_period": progress[goal.id].amount_in_period,
        }
        for goal in overlapping
    ]

    return {
        "period_start": period_start,
        "period_end": period_end,
        "period_days": period_days,
        "items": items,
    }


def get_goal_calendar(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    recorded_from: datetime,
    recorded_to: datetime,
) -> list[dict[str, Any]]:
    """Return per-day goal marks for a range, grouped in the user's timezone.

    Each day includes distinct goals pinned with ``show_in_stats`` (same goal
    linked from several notes counts once), ordered by most recent entry
    ``recorded_at`` then ``sort_order``, capped at ``stats_visible_goal_limit``.
    ``entry_count`` is the unique pinned-goal count for that day.
    """
    tz = _resolve_user_tz(timezone_name)
    from_utc = _to_utc(recorded_from)
    to_utc = _to_utc(recorded_to)
    if to_utc <= from_utc:
        raise GoalError(
            "recorded_to must be after recorded_from", code=ErrorCode.RECORDED_TO_BEFORE_FROM
        )

    calendar_cap = settings.stats_visible_goal_limit
    rows = list(
        db.execute(
            select(MoodEntry.recorded_at, MoodEntryGoal.goal_id)
            .join(MoodEntry, MoodEntry.id == MoodEntryGoal.mood_entry_id)
            .join(Goal, Goal.id == MoodEntryGoal.goal_id)
            .where(
                MoodEntry.user_id == user_id,
                MoodEntry.recorded_at >= from_utc,
                MoodEntry.recorded_at < to_utc,
                Goal.show_in_stats.is_(True),
            )
            .order_by(
                MoodEntry.recorded_at.desc(),
                MoodEntry.created_at.desc(),
                Goal.sort_order.asc(),
            )
        ).all()
    )

    by_day: dict[date, list[uuid.UUID]] = defaultdict(list)
    for recorded_at, goal_id in rows:
        by_day[_local_date(recorded_at, tz)].append(goal_id)

    days: list[dict[str, Any]] = []
    for day in sorted(by_day.keys()):
        goal_ids = _unique_preserve_order(by_day[day])
        days.append(
            {
                "date": day.isoformat(),
                "entry_count": len(goal_ids),
                "goals": [{"goal_id": goal_id} for goal_id in goal_ids[:calendar_cap]],
            }
        )
    return days


def _unique_preserve_order(goal_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    unique: list[uuid.UUID] = []
    for goal_id in goal_ids:
        if goal_id in seen:
            continue
        seen.add(goal_id)
        unique.append(goal_id)
    return unique


def serialize_goals(
    goals: list[Goal],
    *,
    locale: str,
    completed_by_goal: dict[uuid.UUID, int] | None = None,
    day_amount_by_goal: dict[uuid.UUID, int] | None = None,
) -> list[dict[str, Any]]:
    counts = completed_by_goal or {}
    day_amounts = day_amount_by_goal or {}
    return [
        serialize_goal(
            goal,
            locale=locale,
            completed_this_week=counts.get(goal.id, 0),
            day_amount=day_amounts.get(goal.id, 0),
        )
        for goal in goals
    ]


def load_goals_week_stats(
    db: Session,
    *,
    user: User,
    goals: list[Goal],
    reference_date: date | None = None,
) -> dict[uuid.UUID, GoalPeriodProgress]:
    tz = _resolve_user_tz(user.timezone)
    today = reference_date if reference_date is not None else datetime.now(tz).date()
    week_start, week_end = _iso_week_bounds(today)
    progress = period_goal_progress(
        db,
        user_id=user.id,
        timezone_name=user.timezone,
        period_start=week_start,
        period_end=week_end,
        goal_ids=[goal.id for goal in goals],
    )
    for goal in goals:
        if goal.id not in progress:
            progress[goal.id] = GoalPeriodProgress(
                completed_days=0,
                daily_amounts={},
                tracking_kind=goal.tracking_kind,
                target_amount=goal.target_amount,
            )
    return progress


def _resolve_user_tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise GoalError(
            f"Unknown timezone: {timezone_name}",
            code=ErrorCode.UNKNOWN_TIMEZONE,
            status_code=400,
            params={"timezone": timezone_name},
        ) from exc


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _local_date(recorded_at: datetime, tz: ZoneInfo) -> date:
    instant = recorded_at if recorded_at.tzinfo is not None else recorded_at.replace(tzinfo=UTC)
    return instant.astimezone(tz).date()


def _validate_goal_style(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID | None,
    color: str,
    icon_type: str,
    icon: str,
) -> dict[str, str]:
    if not is_valid_hex_color(color):
        raise GoalError(
            f"Invalid color: {color!r}", code=ErrorCode.INVALID_COLOR, params={"color": color}
        )

    try:
        resolved_type = MoodScoreIconType(icon_type)
    except ValueError as exc:
        raise GoalError(
            f"Unknown icon type: {icon_type!r}",
            code=ErrorCode.UNKNOWN_ICON_TYPE,
            params={"icon_type": icon_type},
        ) from exc

    if not isinstance(icon, str) or not icon.strip():
        raise GoalError("Icon must be a non-empty string", code=ErrorCode.ICON_REQUIRED)
    resolved_icon = icon.strip()

    if resolved_type is MoodScoreIconType.EMOJI:
        if len(resolved_icon) > _MAX_EMOJI_LENGTH:
            raise GoalError(
                f"Emoji must be at most {_MAX_EMOJI_LENGTH} characters",
                code=ErrorCode.EMOJI_TOO_LONG,
                params={"max": str(_MAX_EMOJI_LENGTH)},
            )
    elif resolved_type is MoodScoreIconType.BUILTIN:
        if not is_valid_builtin_icon_slug(resolved_icon):
            raise GoalError(
                f"Unknown built-in icon: {resolved_icon!r}",
                code=ErrorCode.UNKNOWN_BUILTIN_ICON,
                params={"icon": resolved_icon},
            )
    elif resolved_type is MoodScoreIconType.UPLOAD:
        if goal_id is None:
            raise GoalError(
                "Uploaded icons can only be set after the goal is created",
                code=ErrorCode.UPLOAD_ICON_BEFORE_CREATE,
            )
        if not _icon_belongs_to_goal(
            db,
            user_id=user_id,
            goal_id=goal_id,
            icon_id=resolved_icon,
        ):
            raise GoalError(
                "Uploaded icon was not found for this goal", code=ErrorCode.UPLOADED_ICON_NOT_FOUND
            )
    elif resolved_type is MoodScoreIconType.CATALOG:
        from app.services.marketplace_service import can_assign_catalog_icon

        if not can_assign_catalog_icon(db, user_id=user_id, icon_id=resolved_icon):
            raise GoalError(
                "Catalog icon is not assignable",
                code=ErrorCode.CATALOG_ICON_NOT_ASSIGNABLE,
            )

    return {
        "color": color,
        "icon_type": resolved_type.value,
        "icon": resolved_icon,
    }


def _icon_belongs_to_goal(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    icon_id: str,
) -> bool:
    try:
        parsed_id = uuid.UUID(icon_id)
    except ValueError:
        return False
    row = db.scalar(
        select(UserGoalIcon.id).where(
            UserGoalIcon.id == parsed_id,
            UserGoalIcon.user_id == user_id,
            UserGoalIcon.goal_id == goal_id,
        )
    )
    return row is not None


def _iso_week_bounds(day: date) -> tuple[date, date]:
    week_start = day - timedelta(days=day.weekday())
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def _validate_goal_dates(*, starts_on: date, ends_on: date | None) -> None:
    if ends_on is not None and ends_on < starts_on:
        raise GoalError(
            "ends_on must be on or after starts_on", code=ErrorCode.ENDS_ON_BEFORE_STARTS_ON
        )


def _validate_tracking(
    *,
    tracking_kind: str | GoalTrackingKind,
    target_amount: int | None,
    unit: str | None,
) -> tuple[GoalTrackingKind, int | None, str | None]:
    try:
        kind = GoalTrackingKind(tracking_kind)
    except ValueError as exc:
        raise GoalError(
            f"Unknown tracking kind: {tracking_kind!r}",
            code=ErrorCode.INVALID_GOAL_TRACKING_KIND,
            params={"tracking_kind": str(tracking_kind)},
        ) from exc

    resolved_unit = unit.strip() if isinstance(unit, str) else unit
    if resolved_unit == "":
        resolved_unit = None
    if resolved_unit is not None and len(resolved_unit) > MAX_GOAL_UNIT_LENGTH:
        raise GoalError(
            f"Unit must be at most {MAX_GOAL_UNIT_LENGTH} characters",
            code=ErrorCode.INVALID_GOAL_UNIT,
            params={"max": str(MAX_GOAL_UNIT_LENGTH)},
        )

    if kind is GoalTrackingKind.BINARY:
        return kind, None, None

    if target_amount is None:
        raise GoalError(
            "Quantity goals need a daily target amount",
            code=ErrorCode.GOAL_TARGET_AMOUNT_REQUIRED,
        )
    if target_amount < 1 or target_amount > MAX_GOAL_AMOUNT:
        raise GoalError(
            f"Target amount must be between 1 and {MAX_GOAL_AMOUNT}",
            code=ErrorCode.INVALID_GOAL_AMOUNT,
            params={"max": str(MAX_GOAL_AMOUNT)},
        )
    return kind, target_amount, resolved_unit


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
            code=ErrorCode.GOAL_VISIBILITY_LIMIT,
            status_code=400,
            params={"limit": str(limit)},
        )


def _count_stats_goals(db: Session, *, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(Goal)
        .where(Goal.user_id == user_id, Goal.show_in_stats.is_(True))
    )
    return int(count or 0)


def _ensure_stats_slot_available(db: Session, *, user_id: uuid.UUID) -> None:
    limit = settings.stats_visible_goal_limit
    if _count_stats_goals(db, user_id=user_id) >= limit:
        raise GoalError(
            f"You can show at most {limit} goals in stats and calendar",
            code=ErrorCode.GOAL_STATS_VISIBILITY_LIMIT,
            status_code=400,
            params={"limit": str(limit)},
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
