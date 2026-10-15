from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.default_tag_groups import (
    DEFAULT_TAG_COLOR,
    DEFAULT_TAG_ICON,
    DEFAULT_TAG_ICON_TYPE,
)
from app.core.emoji import is_single_emoji
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.core.mood_builtin_icons import is_valid_builtin_icon_slug
from app.core.mood_scale import MoodScoreIconType, is_valid_hex_color
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_tag import MoodEntryTag
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_tag_icon import UserTagIcon

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")
_MAX_EMOJI_LENGTH = 8
FREQUENT_TAGS_LIMIT = 8
FREQUENT_TAGS_DAYS = 30


class TagError(AppError):
    pass


def list_tag_groups(db: Session, *, user_id: uuid.UUID) -> list[TagGroup]:
    return list(
        db.scalars(
            select(TagGroup)
            .options(selectinload(TagGroup.tags))
            .where(TagGroup.user_id == user_id)
            .order_by(TagGroup.sort_order, TagGroup.slug)
        ).all()
    )


def get_tag_group(db: Session, *, user_id: uuid.UUID, group_id: uuid.UUID) -> TagGroup:
    group = db.scalar(
        select(TagGroup)
        .options(selectinload(TagGroup.tags))
        .where(TagGroup.id == group_id, TagGroup.user_id == user_id)
    )
    if group is None:
        raise TagError("Tag group not found", code=ErrorCode.TAG_GROUP_NOT_FOUND, status_code=404)
    return group


def create_tag_group(
    db: Session,
    *,
    user_id: uuid.UUID,
    labels: dict[str, str],
    slug: str | None = None,
    sort_order: int | None = None,
    show_on_entry: bool = False,
) -> TagGroup:
    if show_on_entry:
        _ensure_visible_slot_available(db, user_id=user_id)
    resolved_slug = slug or _unique_group_slug(db, user_id=user_id, base=_slugify(labels))
    resolved_order = (
        sort_order
        if sort_order is not None
        else _next_sort_order(
            db,
            select(func.max(TagGroup.sort_order)).where(TagGroup.user_id == user_id),
        )
    )
    group = TagGroup(
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        sort_order=resolved_order,
        show_on_entry=show_on_entry,
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Tag group slug already exists", code=ErrorCode.TAG_GROUP_SLUG_EXISTS, status_code=409
        ) from exc
    return get_tag_group(db, user_id=user_id, group_id=group.id)


def patch_tag_group(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    slug: str | None = None,
    labels: dict[str, str] | None = None,
    sort_order: int | None = None,
    show_on_entry: bool | None = None,
) -> TagGroup:
    group = get_tag_group(db, user_id=user_id, group_id=group_id)
    if slug is not None:
        group.slug = slug
    if labels is not None:
        group.labels = labels
    if sort_order is not None:
        group.sort_order = sort_order
    if show_on_entry is not None and show_on_entry != group.show_on_entry:
        if show_on_entry:
            _ensure_visible_slot_available(db, user_id=user_id)
        group.show_on_entry = show_on_entry
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Tag group slug already exists", code=ErrorCode.TAG_GROUP_SLUG_EXISTS, status_code=409
        ) from exc
    return get_tag_group(db, user_id=user_id, group_id=group_id)


def delete_tag_group(db: Session, *, user_id: uuid.UUID, group_id: uuid.UUID) -> None:
    group = get_tag_group(db, user_id=user_id, group_id=group_id)
    if _group_has_linked_tags(db, group_id=group.id):
        raise TagError(
            "Cannot delete tag group while its tags are used by mood entries",
            code=ErrorCode.TAG_GROUP_IN_USE,
            status_code=409,
        )
    db.delete(group)
    db.commit()


def reorder_tag_groups(
    db: Session,
    *,
    user_id: uuid.UUID,
    ordered_ids: list[uuid.UUID],
) -> list[TagGroup]:
    groups = list_tag_groups(db, user_id=user_id)
    by_id = {group.id: group for group in groups}
    if set(ordered_ids) != set(by_id):
        raise TagError(
            "ordered_ids must include every tag group exactly once",
            code=ErrorCode.TAG_GROUP_REORDER_MISMATCH,
            status_code=400,
        )
    for index, group_id in enumerate(ordered_ids):
        by_id[group_id].sort_order = index
    db.commit()
    return list_tag_groups(db, user_id=user_id)


def create_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    labels: dict[str, str],
    slug: str | None = None,
    sort_order: int | None = None,
    color: str | None = None,
    icon_type: str | None = None,
    icon: str | None = None,
) -> Tag:
    group = get_tag_group(db, user_id=user_id, group_id=group_id)
    resolved_slug = slug or _unique_tag_slug(db, group_id=group.id, base=_slugify(labels))
    resolved_order = (
        sort_order
        if sort_order is not None
        else _next_sort_order(
            db,
            select(func.max(Tag.sort_order)).where(Tag.group_id == group.id),
        )
    )
    style = _validate_tag_style(
        db,
        user_id=user_id,
        tag_id=None,
        color=color if color is not None else DEFAULT_TAG_COLOR,
        icon_type=icon_type if icon_type is not None else DEFAULT_TAG_ICON_TYPE,
        icon=icon if icon is not None else DEFAULT_TAG_ICON,
    )
    tag = Tag(
        group_id=group.id,
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        sort_order=resolved_order,
        color=style["color"],
        icon_type=style["icon_type"],
        icon=style["icon"],
    )
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Tag slug already exists in this group", code=ErrorCode.TAG_SLUG_EXISTS, status_code=409
        ) from exc
    return get_owned_tag(db, user_id=user_id, tag_id=tag.id)


def patch_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    slug: str | None = None,
    labels: dict[str, str] | None = None,
    sort_order: int | None = None,
    color: str | None = None,
    icon_type: str | None = None,
    icon: str | None = None,
) -> Tag:
    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    if tag.group_id != group_id:
        raise TagError(
            "Tag not found in this group", code=ErrorCode.TAG_NOT_FOUND_IN_GROUP, status_code=404
        )
    if slug is not None:
        tag.slug = slug
    if labels is not None:
        tag.labels = labels
    if sort_order is not None:
        tag.sort_order = sort_order
    if color is not None or icon_type is not None or icon is not None:
        style = _validate_tag_style(
            db,
            user_id=user_id,
            tag_id=tag.id,
            color=color if color is not None else tag.color,
            icon_type=icon_type if icon_type is not None else tag.icon_type,
            icon=icon if icon is not None else tag.icon,
        )
        tag.color = style["color"]
        tag.icon_type = style["icon_type"]
        tag.icon = style["icon"]
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Tag slug already exists in this group", code=ErrorCode.TAG_SLUG_EXISTS, status_code=409
        ) from exc
    return get_owned_tag(db, user_id=user_id, tag_id=tag_id)


def delete_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> None:
    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    if tag.group_id != group_id:
        raise TagError(
            "Tag not found in this group", code=ErrorCode.TAG_NOT_FOUND_IN_GROUP, status_code=404
        )
    if _tag_is_linked(db, tag_id=tag.id):
        raise TagError(
            "Cannot delete tag while it is used by mood entries",
            code=ErrorCode.TAG_IN_USE,
            status_code=409,
        )
    db.delete(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Cannot delete tag while it is used by mood entries",
            code=ErrorCode.TAG_IN_USE,
            status_code=409,
        ) from exc


def reorder_tags(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    ordered_ids: list[uuid.UUID],
) -> TagGroup:
    group = get_tag_group(db, user_id=user_id, group_id=group_id)
    by_id = {tag.id: tag for tag in group.tags}
    if set(ordered_ids) != set(by_id):
        raise TagError(
            "ordered_ids must include every tag in the group exactly once",
            code=ErrorCode.TAG_REORDER_MISMATCH,
            status_code=400,
        )
    for index, tag_id in enumerate(ordered_ids):
        by_id[tag_id].sort_order = index
    db.commit()
    return get_tag_group(db, user_id=user_id, group_id=group_id)


def serialize_tag(tag: Tag, *, locale: str) -> dict[str, Any]:
    return {
        "id": tag.id,
        "slug": tag.slug,
        "label": resolve_label(tag.labels, locale),
        "labels": tag.labels,
        "group_id": tag.group_id,
        "sort_order": tag.sort_order,
        "color": tag.color,
        "icon_type": tag.icon_type,
        "icon": tag.icon,
    }


def serialize_tag_group(group: TagGroup, *, locale: str) -> dict[str, Any]:
    tags = [
        serialize_tag(tag, locale=locale)
        for tag in sorted(group.tags, key=lambda item: (item.sort_order, item.slug))
    ]
    return {
        "id": group.id,
        "slug": group.slug,
        "label": resolve_label(group.labels, locale),
        "labels": group.labels,
        "sort_order": group.sort_order,
        "show_on_entry": group.show_on_entry,
        "tags": tags,
    }


def serialize_tag_groups(groups: list[TagGroup], *, locale: str) -> list[dict[str, Any]]:
    return [serialize_tag_group(group, locale=locale) for group in groups]


def list_frequent_tags(
    db: Session,
    *,
    user: User,
    limit: int | None = None,
    days: int | None = None,
) -> list[Tag]:
    """Tags the user selected most often in the recent lookback window."""
    window_days = days if days is not None else FREQUENT_TAGS_DAYS
    result_limit = limit if limit is not None else FREQUENT_TAGS_LIMIT
    since = _frequent_tags_since(user.timezone, days=window_days)
    usage_count = func.count().label("usage_count")
    last_used = func.max(MoodEntry.recorded_at).label("last_used")
    ranked = (
        select(Tag.id, usage_count, last_used)
        .join(MoodEntryTag, MoodEntryTag.tag_id == Tag.id)
        .join(MoodEntry, MoodEntry.id == MoodEntryTag.mood_entry_id)
        .where(
            Tag.user_id == user.id,
            MoodEntry.user_id == user.id,
            MoodEntry.recorded_at >= since,
        )
        .group_by(Tag.id)
        .order_by(usage_count.desc(), last_used.desc(), Tag.slug)
        .limit(result_limit)
    )
    ranked_ids = [row[0] for row in db.execute(ranked).all()]
    if not ranked_ids:
        return []
    tags_by_id = {
        tag.id: tag for tag in db.scalars(select(Tag).where(Tag.id.in_(ranked_ids))).all()
    }
    return [tags_by_id[tag_id] for tag_id in ranked_ids if tag_id in tags_by_id]


def serialize_frequent_tags(db: Session, *, user: User, locale: str) -> list[dict[str, Any]]:
    return [serialize_tag(tag, locale=locale) for tag in list_frequent_tags(db, user=user)]


def _frequent_tags_since(timezone_name: str, *, days: int) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    now_local = datetime.now(tz)
    start_local = (now_local - timedelta(days=days)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start_local.astimezone(UTC)


def _count_visible_groups(db: Session, *, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(TagGroup)
        .where(TagGroup.user_id == user_id, TagGroup.show_on_entry.is_(True))
    )
    return int(count or 0)


def _ensure_visible_slot_available(db: Session, *, user_id: uuid.UUID) -> None:
    limit = settings.entry_visible_tag_group_limit
    if _count_visible_groups(db, user_id=user_id) >= limit:
        raise TagError(
            f"You can show at most {limit} tag groups on the entry form",
            code=ErrorCode.TAG_GROUP_VISIBILITY_LIMIT,
            status_code=400,
            params={"limit": str(limit)},
        )


def get_owned_tag(db: Session, *, user_id: uuid.UUID, tag_id: uuid.UUID) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    if tag is None:
        raise TagError("Tag not found", code=ErrorCode.TAG_NOT_FOUND, status_code=404)
    return tag


def _validate_tag_style(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID | None,
    color: str,
    icon_type: str,
    icon: str,
) -> dict[str, str]:
    if not is_valid_hex_color(color):
        raise TagError(
            f"Invalid color: {color!r}", code=ErrorCode.INVALID_COLOR, params={"color": color}
        )

    try:
        resolved_type = MoodScoreIconType(icon_type)
    except ValueError as exc:
        raise TagError(
            f"Unknown icon type: {icon_type!r}",
            code=ErrorCode.UNKNOWN_ICON_TYPE,
            params={"icon_type": icon_type},
        ) from exc

    if not isinstance(icon, str) or not icon.strip():
        raise TagError("Icon must be a non-empty string", code=ErrorCode.ICON_REQUIRED)
    resolved_icon = icon.strip()

    if resolved_type is MoodScoreIconType.EMOJI:
        if len(resolved_icon) > _MAX_EMOJI_LENGTH:
            raise TagError(
                f"Emoji must be at most {_MAX_EMOJI_LENGTH} characters",
                code=ErrorCode.EMOJI_TOO_LONG,
                params={"max": str(_MAX_EMOJI_LENGTH)},
            )
        if not is_single_emoji(resolved_icon):
            raise TagError("Icon must be a single emoji", code=ErrorCode.INVALID_EMOJI)
    elif resolved_type is MoodScoreIconType.BUILTIN:
        if not is_valid_builtin_icon_slug(resolved_icon):
            raise TagError(
                f"Unknown built-in icon: {resolved_icon!r}",
                code=ErrorCode.UNKNOWN_BUILTIN_ICON,
                params={"icon": resolved_icon},
            )
    elif resolved_type is MoodScoreIconType.UPLOAD:
        if tag_id is None:
            raise TagError(
                "Uploaded icons can only be set after the tag is created",
                code=ErrorCode.UPLOAD_ICON_BEFORE_CREATE,
            )
        if not _icon_belongs_to_tag(
            db,
            user_id=user_id,
            tag_id=tag_id,
            icon_id=resolved_icon,
        ):
            raise TagError(
                "Uploaded icon was not found for this tag", code=ErrorCode.UPLOADED_ICON_NOT_FOUND
            )
    elif resolved_type is MoodScoreIconType.CATALOG:
        from app.services.marketplace_service import can_assign_catalog_icon

        if not can_assign_catalog_icon(db, user_id=user_id, icon_id=resolved_icon):
            raise TagError(
                "Catalog icon is not assignable",
                code=ErrorCode.CATALOG_ICON_NOT_ASSIGNABLE,
            )

    return {
        "color": color,
        "icon_type": resolved_type.value,
        "icon": resolved_icon,
    }


def _icon_belongs_to_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    icon_id: str,
) -> bool:
    try:
        parsed_id = uuid.UUID(icon_id)
    except ValueError:
        return False
    row = db.scalar(
        select(UserTagIcon.id).where(
            UserTagIcon.id == parsed_id,
            UserTagIcon.user_id == user_id,
            UserTagIcon.tag_id == tag_id,
        )
    )
    return row is not None


def _tag_is_linked(db: Session, *, tag_id: uuid.UUID) -> bool:
    count = db.scalar(
        select(func.count()).select_from(MoodEntryTag).where(MoodEntryTag.tag_id == tag_id)
    )
    return bool(count)


def _group_has_linked_tags(db: Session, *, group_id: uuid.UUID) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(MoodEntryTag)
        .join(Tag, Tag.id == MoodEntryTag.tag_id)
        .where(Tag.group_id == group_id)
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
        slug = f"t_{slug}"
    return slug[:64]


def _unique_group_slug(db: Session, *, user_id: uuid.UUID, base: str) -> str:
    return _unique_slug(
        base,
        exists=lambda candidate: (
            db.scalar(
                select(TagGroup.id).where(TagGroup.user_id == user_id, TagGroup.slug == candidate)
            )
            is not None
        ),
    )


def _unique_tag_slug(db: Session, *, group_id: uuid.UUID, base: str) -> str:
    return _unique_slug(
        base,
        exists=lambda candidate: (
            db.scalar(select(Tag.id).where(Tag.group_id == group_id, Tag.slug == candidate))
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
