"""Restore a diary from export archives: preview, add parts, apply or cancel (GP-20).

The restore merges into the current diary. Entries already present (same id, or
restored earlier from the same archive id) are skipped; tag groups, tags, goals and
note templates are matched by slug and created only when missing. Account settings
and reminders are never touched. Everything a restore creates carries its
``restore_id``, and restored entries also get ``source = "restore"``.
"""

from __future__ import annotations

import contextlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import IO, Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.attachment_kind import AttachmentKind
from app.core.default_tag_groups import DEFAULT_TAG_COLOR, DEFAULT_TAG_ICON
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.body import FoodLog, Measurement
from app.models.diary_restore import DiaryRestore, DiaryRestoreStatus
from app.models.goal import DEFAULT_GOAL_COLOR, DEFAULT_GOAL_ICON, Goal
from app.models.goal_checkin import GoalCheckin
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MAX_PHOTOS_PER_ENTRY, MoodEntryAttachment
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.services.achievements.service import evaluate_user_achievements
from app.services.diary_archive.reader import ArchiveError, ArchivePart
from app.services.diary_archive.schema import (
    ArchiveAttachment,
    ArchiveEntry,
    ArchiveGoal,
    ArchiveTag,
    DiaryArchive,
)
from app.services.diary_archive.upgrades import ArchiveWarning
from app.services.embedding_service import upsert_entry_embedding
from app.services.mood_entry_service import (
    ALLOWED_AUDIO_MIME_TYPES,
    ALLOWED_PHOTO_MIME_TYPES,
    MAX_AUDIO_BYTES,
    MAX_PHOTO_BYTES,
    _build_storage_key,
    _score_color_for_user,
)
from app.services.storage import ObjectStorage, StorageError

RESTORE_SOURCE = "restore"
TEMP_PREFIX = "restores"
# Previews nobody confirmed are discarded, with their uploaded files, after this long.
STALE_PREVIEW_AFTER = timedelta(hours=24)
_STALE_BATCH = 50
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_SAFE_ICON_TYPES = frozenset({"emoji", "builtin"})


class RestoreError(AppError):
    pass


@dataclass
class _Diary:
    """What the user's diary already has, keyed the way the archive refers to it."""

    entry_ids: set[uuid.UUID]
    groups: dict[str, TagGroup]
    tags: dict[tuple[str, str], Tag]
    goals: dict[str, Goal]
    templates: dict[str, NoteTemplate]


@dataclass
class _Counts:
    entries_new: int = 0
    tag_groups_new: int = 0
    tags_new: int = 0
    goals_new: int = 0
    note_templates_new: int = 0
    attachments_ready: int = 0
    stored_keys: list[str] = field(default_factory=list)


def _load_diary(db: Session, *, user_id: uuid.UUID, archive: DiaryArchive) -> _Diary:
    archive_ids = {entry.id for entry in archive.entries}
    matched: set[uuid.UUID] = set()
    if archive_ids:
        rows = db.execute(
            select(MoodEntry.id, MoodEntry.origin_id).where(
                MoodEntry.user_id == user_id,
                or_(MoodEntry.id.in_(archive_ids), MoodEntry.origin_id.in_(archive_ids)),
            )
        )
        for entry_id, origin_id in rows:
            matched.update(value for value in (entry_id, origin_id) if value in archive_ids)

    groups = {
        group.slug: group
        for group in db.scalars(select(TagGroup).where(TagGroup.user_id == user_id))
    }
    group_slugs = {group.id: slug for slug, group in groups.items()}
    tags = {
        (group_slugs[tag.group_id], tag.slug): tag
        for tag in db.scalars(select(Tag).where(Tag.user_id == user_id))
        if tag.group_id in group_slugs
    }
    goals = {goal.slug: goal for goal in db.scalars(select(Goal).where(Goal.user_id == user_id))}
    templates = {
        template.slug: template
        for template in db.scalars(select(NoteTemplate).where(NoteTemplate.user_id == user_id))
    }
    return _Diary(entry_ids=matched, groups=groups, tags=tags, goals=goals, templates=templates)


def _new_entries(archive: DiaryArchive, diary: _Diary) -> list[ArchiveEntry]:
    seen: set[uuid.UUID] = set()
    result = []
    for entry in archive.entries:
        if entry.id in diary.entry_ids or entry.id in seen:
            continue
        seen.add(entry.id)
        result.append(entry)
    return result


def _attachment_allowed(attachment: ArchiveAttachment, size: int) -> bool:
    if size <= 0:
        return False
    if attachment.kind == "photo":
        return attachment.mime_type in ALLOWED_PHOTO_MIME_TYPES and size <= MAX_PHOTO_BYTES
    return attachment.mime_type in ALLOWED_AUDIO_MIME_TYPES and size <= MAX_AUDIO_BYTES


def _reference_warnings(archive: DiaryArchive, entries: list[ArchiveEntry]) -> list[ArchiveWarning]:
    """Tags or goals an entry names that the archive itself does not define."""
    known_tags = {(group.slug, tag.slug) for group in archive.tag_groups for tag in group.tags}
    known_goals = {goal.slug for goal in archive.goals}
    unknown_tags = {
        tag.slug
        for entry in entries
        for tag in entry.tags
        if (tag.group, tag.slug) not in known_tags
    }
    unknown_goals = {
        goal.slug for entry in entries for goal in entry.goals if goal.slug not in known_goals
    }
    return [{"code": "unknown_tag", "slug": slug} for slug in sorted(unknown_tags)] + [
        {"code": "unknown_goal", "slug": slug} for slug in sorted(unknown_goals)
    ]


def _summarize(
    archive: DiaryArchive,
    diary: _Diary,
    stored_files: dict[str, str],
    warnings: list[ArchiveWarning],
) -> dict[str, Any]:
    new = _new_entries(archive, diary)
    # Files that were in the upload but rejected are not "missing": re-uploading won't help.
    rejected = {item["file"] for item in warnings if item.get("code") == "invalid_attachment"}
    attachments = [item for entry in new for item in entry.attachments]
    all_parts = [item.part for entry in archive.entries for item in entry.attachments if item.part]
    missing_parts = {
        item.part
        for item in attachments
        if item.file is not None
        and item.file not in stored_files
        and item.file not in rejected
        and item.part is not None
    }
    recorded = sorted(entry.recorded_at for entry in new)
    return {
        "entries_total": len(archive.entries),
        "entries_new": len(new),
        "entries_existing": len(archive.entries) - len(new),
        "first_recorded_at": recorded[0].isoformat() if recorded else None,
        "last_recorded_at": recorded[-1].isoformat() if recorded else None,
        "tag_groups_new": sum(1 for group in archive.tag_groups if group.slug not in diary.groups),
        "tags_new": sum(
            1
            for group in archive.tag_groups
            for tag in group.tags
            if (group.slug, tag.slug) not in diary.tags
        ),
        "goals_new": sum(1 for goal in archive.goals if goal.slug not in diary.goals),
        "note_templates_new": sum(
            1 for template in archive.note_templates if template.slug not in diary.templates
        ),
        "attachments_total": sum(1 for item in attachments if item.file is not None),
        "attachments_ready": sum(1 for item in attachments if item.file in stored_files),
        "attachments_lost": sum(1 for item in attachments if item.file is None),
        "parts_total": max(all_parts, default=1),
        "missing_parts": sorted(missing_parts),
    }


def _archive_of(restore: DiaryRestore) -> DiaryArchive:
    return DiaryArchive.model_validate(restore.archive or {})


def _refresh_preview(db: Session, restore: DiaryRestore) -> None:
    archive = _archive_of(restore)
    diary = _load_diary(db, user_id=restore.user_id, archive=archive)
    restore.summary = _summarize(archive, diary, restore.stored_files, restore.warnings)


def _store_parts(
    restore: DiaryRestore,
    archive: DiaryArchive,
    parts: list[ArchivePart],
    storage: ObjectStorage,
    new_keys: list[str],
) -> None:
    """Copy the attachment files the archive expects into temporary storage."""
    expected = {
        item.file: item
        for entry in archive.entries
        for item in entry.attachments
        if item.file is not None
    }
    stored = dict(restore.stored_files)
    warnings = list(restore.warnings)
    for part in parts:
        matched = part.names & expected.keys()
        if not matched and not part.has_diary:
            raise RestoreError(
                "This file is not a part of the archive being restored",
                code=ErrorCode.RESTORE_PART_UNKNOWN,
            )
        for name in sorted(matched):
            if name in stored:
                continue
            attachment = expected[name]
            if not _attachment_allowed(attachment, part.size(name)):
                warning = {"code": "invalid_attachment", "file": name}
                if warning not in warnings:
                    warnings.append(warning)
                continue
            key = f"{TEMP_PREFIX}/{restore.user_id}/{restore.id}/{uuid.uuid4()}"
            storage.put_object(key=key, data=part.read(name), content_type=attachment.mime_type)
            new_keys.append(key)
            stored[name] = key
    restore.stored_files = stored
    restore.warnings = warnings


def _discard(restore: DiaryRestore) -> list[str]:
    """Mark a preview cancelled; return its temporary keys to delete after commit."""
    keys = list(restore.stored_files.values())
    restore.status = DiaryRestoreStatus.CANCELLED.value
    restore.archive = None
    restore.stored_files = {}
    return keys


def _delete_keys(storage: ObjectStorage, keys: list[str]) -> None:
    for key in keys:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=key)


def _discard_stale_previews(db: Session) -> list[str]:
    cutoff = datetime.now(UTC) - STALE_PREVIEW_AFTER
    stale = db.scalars(
        select(DiaryRestore)
        .where(
            DiaryRestore.status == DiaryRestoreStatus.PREVIEW.value,
            DiaryRestore.created_at < cutoff,
        )
        .limit(_STALE_BATCH)
        .with_for_update(skip_locked=True)
    )
    keys: list[str] = []
    for restore in stale:
        keys.extend(_discard(restore))
    return keys


def _open_parts(files: list[IO[bytes]]) -> list[ArchivePart]:
    if not files:
        raise RestoreError("No archive uploaded", code=ErrorCode.RESTORE_DIARY_MISSING)
    return [ArchivePart(handle) for handle in files]


def _get_preview(db: Session, *, user: User, restore_id: uuid.UUID) -> DiaryRestore:
    restore = db.scalar(
        select(DiaryRestore)
        .where(DiaryRestore.id == restore_id, DiaryRestore.user_id == user.id)
        .with_for_update()
    )
    if restore is None:
        raise RestoreError("Restore not found", code=ErrorCode.RESTORE_NOT_FOUND, status_code=404)
    if restore.status != DiaryRestoreStatus.PREVIEW.value:
        raise RestoreError(
            "This restore is already finished",
            code=ErrorCode.RESTORE_NOT_IN_PREVIEW,
            status_code=409,
        )
    return restore


def create_restore(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    files: list[IO[bytes]],
) -> DiaryRestore:
    """Read the uploaded parts and return a preview; nothing in the diary changes yet."""
    parts = _open_parts(files)
    with_diary = [part for part in parts if part.has_diary]
    if not with_diary:
        raise RestoreError(
            "Upload the part that contains diary.json",
            code=ErrorCode.RESTORE_DIARY_MISSING,
        )
    if len(with_diary) > 1:
        raise ArchiveError("Upload one archive at a time", code=ErrorCode.RESTORE_INVALID_ARCHIVE)
    archive, version, warnings = with_diary[0].read_diary()

    keys_to_delete = _discard_stale_previews(db)
    for previous in db.scalars(
        select(DiaryRestore).where(
            DiaryRestore.user_id == user.id,
            DiaryRestore.status == DiaryRestoreStatus.PREVIEW.value,
        )
    ):
        keys_to_delete.extend(_discard(previous))

    restore = DiaryRestore(
        user_id=user.id,
        status=DiaryRestoreStatus.PREVIEW.value,
        format_version=version,
        archive_exported_at=archive.exported_at,
        archive=archive.model_dump(mode="json"),
        stored_files={},
        warnings=list(warnings) + _reference_warnings(archive, archive.entries),
        summary={},
    )
    db.add(restore)
    db.flush()

    new_keys: list[str] = []
    try:
        _store_parts(restore, archive, parts, storage, new_keys)
        _refresh_preview(db, restore)
        db.commit()
    except Exception:
        db.rollback()
        _delete_keys(storage, new_keys)
        raise
    _delete_keys(storage, keys_to_delete)
    db.refresh(restore)
    return restore


def add_restore_parts(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    restore_id: uuid.UUID,
    files: list[IO[bytes]],
) -> DiaryRestore:
    """Add more ZIP parts to a preview, for photos and voice notes that live there."""
    parts = _open_parts(files)
    restore = _get_preview(db, user=user, restore_id=restore_id)
    new_keys: list[str] = []
    try:
        _store_parts(restore, _archive_of(restore), parts, storage, new_keys)
        _refresh_preview(db, restore)
        db.commit()
    except Exception:
        db.rollback()
        _delete_keys(storage, new_keys)
        raise
    db.refresh(restore)
    return restore


def cancel_restore(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    restore_id: uuid.UUID,
) -> DiaryRestore:
    restore = _get_preview(db, user=user, restore_id=restore_id)
    keys = _discard(restore)
    db.commit()
    _delete_keys(storage, keys)
    db.refresh(restore)
    return restore


def _color(value: str | None, fallback: str) -> str:
    return value if value is not None and _HEX_COLOR.match(value) else fallback


def _icon(icon_type: str, icon: str, fallback: str) -> tuple[str, str]:
    # Uploaded and catalog icons point at files of the old account; keep only plain ones.
    if icon_type in _SAFE_ICON_TYPES and icon:
        return icon_type, icon[:64]
    return "emoji", fallback


def _new_tag(
    group: TagGroup, data: ArchiveTag, *, user_id: uuid.UUID, restore_id: uuid.UUID
) -> Tag:
    icon_type, icon = _icon(data.icon_type, data.icon, DEFAULT_TAG_ICON)
    return Tag(
        group_id=group.id,
        user_id=user_id,
        slug=data.slug,
        labels=dict(data.labels),
        sort_order=data.sort_order,
        color=_color(data.color, DEFAULT_TAG_COLOR),
        icon_type=icon_type,
        icon=icon,
        restore_id=restore_id,
    )


def _new_goal(
    data: ArchiveGoal, *, user_id: uuid.UUID, restore_id: uuid.UUID, today: datetime
) -> Goal:
    starts_on = data.starts_on or today.date()
    ends_on = data.ends_on if data.ends_on is None or data.ends_on >= starts_on else None
    quantity = data.tracking_kind == "quantity"
    icon_type, icon = _icon(data.icon_type, data.icon, DEFAULT_GOAL_ICON)
    return Goal(
        user_id=user_id,
        slug=data.slug,
        labels=dict(data.labels),
        tracking_kind=data.tracking_kind,
        times_per_week=data.times_per_week,
        target_amount=(data.target_amount or 1) if quantity else None,
        unit=data.unit if quantity else None,
        partial_label=data.partial_label,
        min_amount=(
            min(data.min_amount, data.target_amount or 1)
            if quantity and data.min_amount is not None
            else None
        ),
        starts_on=starts_on,
        ends_on=ends_on,
        sort_order=data.sort_order,
        show_on_entry=data.show_on_entry,
        show_in_stats=data.show_in_stats,
        color=_color(data.color, DEFAULT_GOAL_COLOR),
        icon_type=icon_type,
        icon=icon,
        restore_id=restore_id,
    )


def _restore_goal_checkins(
    db: Session, archive: DiaryArchive, diary: _Diary, *, user_id: uuid.UUID
) -> None:
    """Add check-ins for days the goal has none yet; existing marks stay as they are."""
    goal_ids = [goal.id for goal in diary.goals.values()]
    taken = {
        (goal_id, day)
        for goal_id, day in db.execute(
            select(GoalCheckin.goal_id, GoalCheckin.day).where(GoalCheckin.goal_id.in_(goal_ids))
        ).all()
    }
    for goal_data in archive.goals:
        goal = diary.goals.get(goal_data.slug)
        if goal is None:
            continue
        for checkin in goal_data.checkins:
            if (goal.id, checkin.day) in taken:
                continue
            taken.add((goal.id, checkin.day))
            db.add(
                GoalCheckin(
                    user_id=user_id,
                    goal_id=goal.id,
                    day=checkin.day,
                    level=checkin.level,
                    amount=checkin.amount if goal.tracking_kind == "quantity" else None,
                )
            )


def _restore_body(db: Session, archive: DiaryArchive, *, user_id: uuid.UUID) -> None:
    """Add weights for days without one and food notes not already there (GP-47)."""
    weighed = set(
        db.scalars(
            select(Measurement.day).where(
                Measurement.user_id == user_id, Measurement.kind == "weight"
            )
        )
    )
    for weight in archive.weights:
        if weight.day in weighed:
            continue
        weighed.add(weight.day)
        db.add(
            Measurement(
                user_id=user_id,
                kind="weight",
                day=weight.day,
                value=Decimal(str(round(weight.value_kg, 1))),
            )
        )
    eaten = {
        (day, meal, text)
        for day, meal, text in db.execute(
            select(FoodLog.day, FoodLog.meal, FoodLog.text).where(FoodLog.user_id == user_id)
        ).all()
    }
    for food in archive.food:
        key = (food.day, food.meal, food.text)
        if key in eaten:
            continue
        eaten.add(key)
        db.add(FoodLog(user_id=user_id, day=food.day, meal=food.meal, text=food.text))


def _restore_setup(
    db: Session, archive: DiaryArchive, diary: _Diary, restore: DiaryRestore, counts: _Counts
) -> None:
    """Create missing tag groups, tags, goals and note templates; reuse the rest as is."""
    user_id, restore_id = restore.user_id, restore.id
    for group_data in archive.tag_groups:
        group = diary.groups.get(group_data.slug)
        if group is None:
            group = TagGroup(
                user_id=user_id,
                slug=group_data.slug,
                labels=dict(group_data.labels),
                sort_order=group_data.sort_order,
                show_on_entry=group_data.show_on_entry,
                restore_id=restore_id,
            )
            db.add(group)
            db.flush()
            diary.groups[group.slug] = group
            counts.tag_groups_new += 1
        for tag_data in group_data.tags:
            key = (group_data.slug, tag_data.slug)
            if key in diary.tags:
                continue
            tag = _new_tag(group, tag_data, user_id=user_id, restore_id=restore_id)
            db.add(tag)
            db.flush()
            diary.tags[key] = tag
            counts.tags_new += 1

    now = datetime.now(UTC)
    for goal_data in archive.goals:
        if goal_data.slug in diary.goals:
            continue
        goal = _new_goal(goal_data, user_id=user_id, restore_id=restore_id, today=now)
        db.add(goal)
        db.flush()
        diary.goals[goal.slug] = goal
        counts.goals_new += 1
    _restore_goal_checkins(db, archive, diary, user_id=user_id)
    _restore_body(db, archive, user_id=user_id)

    for template_data in archive.note_templates:
        if template_data.slug in diary.templates:
            continue
        template = NoteTemplate(
            user_id=user_id,
            slug=template_data.slug,
            labels=dict(template_data.labels),
            bodies=dict(template_data.bodies),
            sort_order=template_data.sort_order,
            restore_id=restore_id,
        )
        db.add(template)
        diary.templates[template.slug] = template
        counts.note_templates_new += 1


def _restore_attachments(
    entry: MoodEntry,
    data: ArchiveEntry,
    *,
    stored_files: dict[str, str],
    storage: ObjectStorage,
    counts: _Counts,
) -> None:
    photo_positions: set[int] = set()
    has_audio = False
    for item in data.attachments:
        temp_key = stored_files.get(item.file) if item.file else None
        if temp_key is None:
            continue
        if item.kind == "photo":
            if len(photo_positions) >= MAX_PHOTOS_PER_ENTRY:
                continue
            position = item.position
            if (
                position is None
                or not 1 <= position <= MAX_PHOTOS_PER_ENTRY
                or (position in photo_positions)
            ):
                position = min(
                    p for p in range(1, MAX_PHOTOS_PER_ENTRY + 1) if p not in photo_positions
                )
            photo_positions.add(position)
            kind = AttachmentKind.PHOTO
        else:
            if has_audio:
                continue
            has_audio = True
            position = None
            kind = AttachmentKind.AUDIO
        try:
            payload = storage.get_object(key=temp_key)
        except StorageError:
            continue
        attachment_id = uuid.uuid4()
        original_name = (item.original_name or item.file or "file").rsplit("/", 1)[-1][:255]
        key = _build_storage_key(
            user_id=entry.user_id,
            entry_id=entry.id,
            attachment_id=attachment_id,
            original_name=original_name,
        )
        storage.put_object(key=key, data=payload, content_type=item.mime_type)
        counts.stored_keys.append(key)
        entry.attachments.append(
            MoodEntryAttachment(
                id=attachment_id,
                kind=kind,
                storage_key=key,
                mime_type=item.mime_type,
                size_bytes=len(payload),
                original_name=original_name,
                position=position,
                transcription=item.transcription,
            )
        )
        counts.attachments_ready += 1


def _restore_entries(
    db: Session,
    archive: DiaryArchive,
    diary: _Diary,
    restore: DiaryRestore,
    storage: ObjectStorage,
    counts: _Counts,
) -> None:
    for data in _new_entries(archive, diary):
        entry = MoodEntry(
            user_id=restore.user_id,
            recorded_at=data.recorded_at.astimezone(UTC),
            logged_on=data.logged_on,
            logged_timezone=data.logged_timezone,
            score=data.score,
            # Keep the color the mood had back then; the palette may have changed since.
            score_color=(
                data.score_color
                if data.score_color and _HEX_COLOR.match(data.score_color)
                else _score_color_for_user(db, user_id=restore.user_id, score=data.score)
            ),
            note=data.note,
            is_favorite=data.is_favorite,
            is_win=data.is_win,
            source=RESTORE_SOURCE,
            origin_id=data.id,
            restore_id=restore.id,
        )
        db.add(entry)
        db.flush()

        linked_tags: set[uuid.UUID] = set()
        for tag_ref in data.tags:
            tag = diary.tags.get((tag_ref.group, tag_ref.slug))
            if tag is None or tag.id in linked_tags:
                continue
            linked_tags.add(tag.id)
            entry.tag_links.append(
                MoodEntryTag(tag_id=tag.id, color=_color(tag_ref.color, tag.color))
            )
        linked_goals: set[uuid.UUID] = set()
        for goal_ref in data.goals:
            goal = diary.goals.get(goal_ref.slug)
            if goal is None or goal.id in linked_goals:
                continue
            linked_goals.add(goal.id)
            entry.goal_links.append(
                MoodEntryGoal(
                    goal_id=goal.id,
                    color=_color(goal_ref.color, goal.color),
                    amount=goal_ref.amount,
                )
            )
        _restore_attachments(
            entry, data, stored_files=restore.stored_files, storage=storage, counts=counts
        )
        upsert_entry_embedding(db, entry)
        counts.entries_new += 1


def apply_restore(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    restore_id: uuid.UUID,
    locale: str = "en",
) -> DiaryRestore:
    """Write the previewed archive into the diary and finish the restore."""
    restore = _get_preview(db, user=user, restore_id=restore_id)
    archive = _archive_of(restore)
    diary = _load_diary(db, user_id=user.id, archive=archive)
    preview = _summarize(archive, diary, restore.stored_files, restore.warnings)
    counts = _Counts()
    try:
        _restore_setup(db, archive, diary, restore, counts)
        _restore_entries(db, archive, diary, restore, storage, counts)
        db.flush()
        evaluate_user_achievements(db, user=user, locale=locale)
        temp_keys = list(restore.stored_files.values())
        restore.summary = {
            **preview,
            "entries_new": counts.entries_new,
            "entries_existing": len(archive.entries) - counts.entries_new,
            "tag_groups_new": counts.tag_groups_new,
            "tags_new": counts.tags_new,
            "goals_new": counts.goals_new,
            "note_templates_new": counts.note_templates_new,
            "attachments_ready": counts.attachments_ready,
        }
        restore.status = DiaryRestoreStatus.APPLIED.value
        restore.applied_at = datetime.now(UTC)
        restore.archive = None
        restore.stored_files = {}
        db.commit()
    except Exception:
        db.rollback()
        _delete_keys(storage, counts.stored_keys)
        raise
    _delete_keys(storage, temp_keys)
    db.refresh(restore)
    return restore


def restore_temp_keys(db: Session, *, user_id: uuid.UUID) -> set[str]:
    """Temporary files of a user's open previews, for account deletion."""
    keys: set[str] = set()
    for stored in db.scalars(
        select(DiaryRestore.stored_files).where(DiaryRestore.user_id == user_id)
    ):
        keys.update(stored.values())
    return keys
