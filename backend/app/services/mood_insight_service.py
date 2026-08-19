"""Load mood entries and turn them into pattern-insight cards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.error_codes import ErrorCode
from app.core.mood_insights import (
    DEFAULT_INSIGHT_LIMIT,
    INSIGHT_DEFAULT_LOOKBACK_DAYS,
    INSIGHT_MAX_WINDOW_DAYS,
    MAX_INSIGHT_LIMIT,
    FocusContext,
    InsightCandidate,
    MoodObservation,
    TagRef,
    build_insights,
    bundle_days,
    daypart_for_hour,
)
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_tag import MoodEntryTag
from app.models.tag import Tag
from app.models.user import User
from app.services.mood_entry_service import (
    MoodEntryError,
    _resolve_user_tz,
    _to_utc,
    get_mood_entry,
)
from app.services.tag_service import serialize_tag


def get_mood_insights(
    db: Session,
    *,
    user: User,
    locale: str,
    recorded_from: datetime | None = None,
    recorded_to: datetime | None = None,
    limit: int = DEFAULT_INSIGHT_LIMIT,
    focus_entry_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    tz = _resolve_user_tz(user.timezone)
    from_utc, to_utc = resolve_insight_window(
        timezone_name=user.timezone,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
        now=now,
    )
    clamped_limit = max(1, min(limit, MAX_INSIGHT_LIMIT))

    entries = list(
        db.scalars(
            select(MoodEntry)
            .options(selectinload(MoodEntry.tag_links).selectinload(MoodEntryTag.tag))
            .where(
                MoodEntry.user_id == user.id,
                MoodEntry.recorded_at >= from_utc,
                MoodEntry.recorded_at < to_utc,
            )
            .order_by(MoodEntry.recorded_at.asc(), MoodEntry.created_at.asc())
        ).all()
    )

    observations: list[MoodObservation] = []
    tags: dict[uuid.UUID, TagRef] = {}
    for entry in entries:
        local = _to_local(entry.recorded_at, tz)
        tag_ids: set[uuid.UUID] = set()
        for link in entry.tag_links:
            tag = link.tag
            tag_ids.add(tag.id)
            if tag.id not in tags:
                tags[tag.id] = _tag_ref(tag, locale=locale)
        observations.append(
            MoodObservation(
                local_date=local.date(),
                weekday=local.weekday(),
                hour=local.hour,
                daypart=daypart_for_hour(local.hour),
                score=int(entry.score),
                tag_ids=frozenset(tag_ids),
                recorded_at=entry.recorded_at,
            )
        )

    focus = _focus_context(db, user=user, tz=tz, entry_id=focus_entry_id)
    items = build_insights(
        observations,
        tags=tags,
        locale=locale,
        limit=clamped_limit,
        focus=focus,
    )

    bundles = bundle_days(observations)
    day_indices = [day.day_index for day in bundles.values()]
    baseline_index = sum(day_indices) / len(day_indices) if day_indices else None

    return {
        "window_from": from_utc,
        "window_to": to_utc,
        "active_days": len(bundles),
        "entry_count": len(observations),
        "baseline_index": baseline_index,
        "items": [_serialize_insight(item) for item in items],
    }


def resolve_insight_window(
    *,
    timezone_name: str,
    recorded_from: datetime | None,
    recorded_to: datetime | None,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """UTC half-open ``[from, to)`` window, clipped to ``INSIGHT_MAX_WINDOW_DAYS``.

    Default: the last ``INSIGHT_DEFAULT_LOOKBACK_DAYS`` local calendar days,
    ending at the start of tomorrow in the user's timezone (so "today" is in).
    """
    tz = _resolve_user_tz(timezone_name)
    if (recorded_from is None) != (recorded_to is None):
        raise MoodEntryError(
            "recorded_from and recorded_to must be sent together",
            code=ErrorCode.RECORDED_RANGE_INCOMPLETE,
            status_code=400,
        )

    if recorded_from is not None and recorded_to is not None:
        from_utc = _to_utc(recorded_from)
        to_utc = _to_utc(recorded_to)
        if to_utc <= from_utc:
            raise MoodEntryError(
                "recorded_to must be after recorded_from",
                code=ErrorCode.RECORDED_TO_BEFORE_FROM,
            )
    else:
        instant = now if now is not None else datetime.now(UTC)
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        local = instant.astimezone(tz)
        end_local = datetime(local.year, local.month, local.day, tzinfo=tz) + timedelta(days=1)
        start_local = end_local - timedelta(days=INSIGHT_DEFAULT_LOOKBACK_DAYS)
        from_utc = start_local.astimezone(UTC)
        to_utc = end_local.astimezone(UTC)

    max_span = timedelta(days=INSIGHT_MAX_WINDOW_DAYS)
    if to_utc - from_utc > max_span:
        from_utc = to_utc - max_span
    return from_utc, to_utc


def _to_local(recorded_at: datetime, tz: ZoneInfo) -> datetime:
    instant = recorded_at if recorded_at.tzinfo is not None else recorded_at.replace(tzinfo=UTC)
    return instant.astimezone(tz)


def _tag_ref(tag: Tag, *, locale: str) -> TagRef:
    payload = serialize_tag(tag, locale=locale)
    return TagRef(
        id=tag.id,
        slug=tag.slug,
        label=str(payload["label"]),
        color=tag.color,
        icon_type=tag.icon_type,
        icon=tag.icon,
    )


def _focus_context(
    db: Session,
    *,
    user: User,
    tz: ZoneInfo,
    entry_id: uuid.UUID | None,
) -> FocusContext | None:
    if entry_id is None:
        return None
    try:
        entry = get_mood_entry(db, user_id=user.id, entry_id=entry_id)
    except MoodEntryError:
        return None
    local = _to_local(entry.recorded_at, tz)
    return FocusContext(
        weekday=local.weekday(),
        daypart=daypart_for_hour(local.hour),
        tag_ids=frozenset(link.tag_id for link in entry.tag_links),
    )


def _serialize_insight(item: InsightCandidate) -> dict[str, object]:
    subjects: list[dict[str, object]] = []
    for subject in item.subjects:
        row: dict[str, object] = {
            "type": subject.type.value,
            "key": subject.key,
            "label": subject.label,
        }
        if subject.tag is not None:
            row.update(
                {
                    "id": subject.tag.id,
                    "slug": subject.tag.slug,
                    "color": subject.tag.color,
                    "icon_type": subject.tag.icon_type,
                    "icon": subject.tag.icon,
                }
            )
        subjects.append(row)
    return {
        "id": item.id,
        "kind": item.kind.value,
        "direction": item.direction.value,
        "strength": item.strength.value,
        "title": item.title,
        "body": item.body,
        "sample": item.sample,
        "stats": {
            "delta": item.delta,
            "lift": item.lift,
            "group_mean": item.group_mean,
            "complement_mean": item.complement_mean,
            "group_share": item.group_share,
            "complement_share": item.complement_share,
            "group_n": item.group_n,
            "complement_n": item.complement_n,
        },
        "subjects": subjects,
    }
