from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.models.mood_entry_tag import MoodEntryTag
from app.models.tag import Tag
from app.models.tag_group import TagGroup

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


class TagError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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
        raise TagError("Tag group not found", status_code=404)
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
        raise TagError("Tag group slug already exists", status_code=409) from exc
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
        raise TagError("Tag group slug already exists", status_code=409) from exc
    return get_tag_group(db, user_id=user_id, group_id=group_id)


def delete_tag_group(db: Session, *, user_id: uuid.UUID, group_id: uuid.UUID) -> None:
    group = get_tag_group(db, user_id=user_id, group_id=group_id)
    if _group_has_linked_tags(db, group_id=group.id):
        raise TagError(
            "Cannot delete tag group while its tags are used by mood entries",
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
        raise TagError("ordered_ids must include every tag group exactly once", status_code=400)
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
    tag = Tag(
        group_id=group.id,
        user_id=user_id,
        slug=resolved_slug,
        labels=labels,
        sort_order=resolved_order,
    )
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError("Tag slug already exists in this group", status_code=409) from exc
    return _get_owned_tag(db, user_id=user_id, tag_id=tag.id)


def patch_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
    slug: str | None = None,
    labels: dict[str, str] | None = None,
    sort_order: int | None = None,
) -> Tag:
    tag = _get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    if tag.group_id != group_id:
        raise TagError("Tag not found in this group", status_code=404)
    if slug is not None:
        tag.slug = slug
    if labels is not None:
        tag.labels = labels
    if sort_order is not None:
        tag.sort_order = sort_order
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError("Tag slug already exists in this group", status_code=409) from exc
    return _get_owned_tag(db, user_id=user_id, tag_id=tag_id)


def delete_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> None:
    tag = _get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    if tag.group_id != group_id:
        raise TagError("Tag not found in this group", status_code=404)
    if _tag_is_linked(db, tag_id=tag.id):
        raise TagError(
            "Cannot delete tag while it is used by mood entries",
            status_code=409,
        )
    db.delete(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TagError(
            "Cannot delete tag while it is used by mood entries",
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
            status_code=400,
        )


def _get_owned_tag(db: Session, *, user_id: uuid.UUID, tag_id: uuid.UUID) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    if tag is None:
        raise TagError("Tag not found", status_code=404)
    return tag


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
        exists=lambda candidate: db.scalar(
            select(TagGroup.id).where(TagGroup.user_id == user_id, TagGroup.slug == candidate)
        )
        is not None,
    )


def _unique_tag_slug(db: Session, *, group_id: uuid.UUID, base: str) -> str:
    return _unique_slug(
        base,
        exists=lambda candidate: db.scalar(
            select(Tag.id).where(Tag.group_id == group_id, Tag.slug == candidate)
        )
        is not None,
    )


def _unique_slug(base: str, *, exists: Callable[[str], bool]) -> str:
    candidate = base
    index = 2
    while exists(candidate):
        suffix = f"_{index}"
        candidate = f"{base[: 64 - len(suffix)]}{suffix}"
        index += 1
    return candidate
