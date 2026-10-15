"""Full personal-data export: one ZIP with JSON, CSV and attachment files."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
import uuid
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from tempfile import SpooledTemporaryFile
from typing import IO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.i18n import resolve_label
from app.models.body import FoodLog, Measurement, SleepLog
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MoodEntryAttachment
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.diary_archive.schema import (
    CURRENT_VERSION,
    ArchiveAccount,
    ArchiveAttachment,
    ArchiveEntry,
    ArchiveEntryGoal,
    ArchiveEntryTag,
    ArchiveFoodLog,
    ArchiveGoal,
    ArchiveGoalCheckin,
    ArchiveNoteTemplate,
    ArchiveReminder,
    ArchiveSleep,
    ArchiveTag,
    ArchiveTagGroup,
    ArchiveWeight,
    DiaryArchive,
)
from app.services.storage import ObjectStorage, StorageError
from app.services.telegram_delivery import ensure_can_deliver, send_to_user_chat

EXPORT_FORMAT_VERSION = CURRENT_VERSION
# Small exports stay in memory; bigger ones (many photos) spill to a temp file.
_SPOOL_MAX_BYTES = 16 * 1024 * 1024
_CHUNK_BYTES = 64 * 1024
# Bot API sendDocument accepts files up to 50 MB; stay well under it.
TELEGRAM_PART_BYTES = 45 * 1024 * 1024
_TELEGRAM_UPLOAD_TIMEOUT = 120.0
_TELEGRAM_CAPTIONS = {
    "ru": ("GlowPath: ваш дневник", "GlowPath: ваш дневник, часть {part} из {total}"),
    "en": ("GlowPath: your diary", "GlowPath: your diary, part {part} of {total}"),
}

CSV_COLUMNS = (
    "date",
    "time",
    "score",
    "note",
    "tags",
    "goals",
    "favorite",
    "photos",
    "audio",
)


def _user_zone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _attachment_path(attachment: MoodEntryAttachment) -> str:
    extension = mimetypes.guess_extension(attachment.mime_type) or ""
    if not extension and "." in attachment.original_name:
        extension = "." + attachment.original_name.rsplit(".", 1)[1][:10]
    return f"attachments/{attachment.mood_entry_id}/{attachment.id}{extension}"


def _load_entries(db: Session, user_id: uuid.UUID) -> list[MoodEntry]:
    return list(
        db.scalars(
            select(MoodEntry)
            .where(MoodEntry.user_id == user_id)
            .options(
                selectinload(MoodEntry.tag_links)
                .selectinload(MoodEntryTag.tag)
                .selectinload(Tag.group),
                selectinload(MoodEntry.goal_links).selectinload(MoodEntryGoal.goal),
                selectinload(MoodEntry.attachments),
            )
            .order_by(MoodEntry.recorded_at, MoodEntry.id)
        )
    )


def _tag_groups_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveTagGroup]:
    groups = db.scalars(
        select(TagGroup)
        .where(TagGroup.user_id == user_id)
        .options(selectinload(TagGroup.tags))
        .order_by(TagGroup.sort_order, TagGroup.created_at)
    )
    return [
        ArchiveTagGroup(
            slug=group.slug,
            labels=group.labels,
            show_on_entry=group.show_on_entry,
            sort_order=group.sort_order,
            tags=[
                ArchiveTag(
                    slug=tag.slug,
                    labels=tag.labels,
                    color=tag.color,
                    sort_order=tag.sort_order,
                    icon_type=tag.icon_type,
                    icon=tag.icon,
                )
                for tag in sorted(group.tags, key=lambda item: (item.sort_order, item.slug))
            ],
        )
        for group in groups
    ]


def _goals_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveGoal]:
    goals = db.scalars(
        select(Goal)
        .where(Goal.user_id == user_id)
        .options(selectinload(Goal.checkins))
        .order_by(Goal.sort_order, Goal.created_at)
    )
    return [
        ArchiveGoal(
            slug=goal.slug,
            labels=goal.labels,
            tracking_kind=goal.tracking_kind,
            times_per_week=goal.times_per_week,
            target_amount=goal.target_amount,
            unit=goal.unit,
            partial_label=goal.partial_label,
            min_amount=goal.min_amount,
            starts_on=goal.starts_on,
            ends_on=goal.ends_on,
            color=goal.color,
            sort_order=goal.sort_order,
            show_on_entry=goal.show_on_entry,
            show_in_stats=goal.show_in_stats,
            icon_type=goal.icon_type,
            icon=goal.icon,
            checkins=[
                ArchiveGoalCheckin(day=checkin.day, level=checkin.level, amount=checkin.amount)
                for checkin in sorted(goal.checkins, key=lambda item: item.day)
            ],
        )
        for goal in goals
    ]


def _note_templates_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveNoteTemplate]:
    templates = db.scalars(
        select(NoteTemplate)
        .where(NoteTemplate.user_id == user_id)
        .order_by(NoteTemplate.sort_order, NoteTemplate.created_at)
    )
    return [
        ArchiveNoteTemplate(
            slug=item.slug, labels=item.labels, bodies=item.bodies, sort_order=item.sort_order
        )
        for item in templates
    ]


def _reminders_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveReminder]:
    schedules = db.scalars(
        select(UserNotificationSchedule)
        .where(UserNotificationSchedule.user_id == user_id)
        .order_by(UserNotificationSchedule.kind)
    )
    return [
        ArchiveReminder(
            kind=item.kind,
            enabled=item.enabled,
            time_of_day=item.time_of_day,
            interval_days=item.interval_days,
            days_of_week=item.days_of_week,
            channels=item.channels,
        )
        for item in schedules
    ]


def _weights_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveWeight]:
    rows = db.scalars(
        select(Measurement)
        .where(Measurement.user_id == user_id, Measurement.kind == "weight")
        .order_by(Measurement.day)
    )
    return [ArchiveWeight(day=row.day, value_kg=float(row.value)) for row in rows]


def _food_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveFoodLog]:
    rows = db.scalars(
        select(FoodLog).where(FoodLog.user_id == user_id).order_by(FoodLog.day, FoodLog.created_at)
    )
    return [ArchiveFoodLog(day=row.day, meal=row.meal, text=row.text) for row in rows]


def _sleep_payload(db: Session, user_id: uuid.UUID) -> list[ArchiveSleep]:
    rows = db.scalars(select(SleepLog).where(SleepLog.user_id == user_id).order_by(SleepLog.day))
    return [
        ArchiveSleep(
            day=row.day,
            bed_time=row.bed_time,
            wake_time=row.wake_time,
            up_time=row.up_time,
            quality=row.quality,
            note=row.note,
        )
        for row in rows
    ]


def _entry_payload(
    entry: MoodEntry,
    files: dict[uuid.UUID, str | None],
    parts: dict[uuid.UUID, int],
) -> ArchiveEntry:
    return ArchiveEntry(
        id=entry.id,
        recorded_at=entry.recorded_at,
        logged_on=entry.logged_on,
        logged_timezone=entry.logged_timezone,
        score=entry.score,
        score_color=entry.score_color,
        note=entry.note,
        is_favorite=entry.is_favorite,
        is_win=entry.is_win,
        tags=[
            ArchiveEntryTag(
                group=link.tag.group.slug,
                slug=link.tag.slug,
                labels=link.tag.labels,
                color=link.color,
            )
            for link in entry.tag_links
        ],
        goals=[
            ArchiveEntryGoal(
                slug=link.goal.slug, labels=link.goal.labels, amount=link.amount, color=link.color
            )
            for link in entry.goal_links
        ],
        attachments=[
            ArchiveAttachment(
                kind=attachment.kind.value,
                file=files.get(attachment.id),
                part=parts.get(attachment.id),
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
                original_name=attachment.original_name,
                position=attachment.position,
                transcription=attachment.transcription,
            )
            for attachment in sorted(
                entry.attachments, key=lambda item: (item.kind.value, item.position or 0)
            )
        ],
    )


def _entries_csv(entries: list[MoodEntry], *, zone: ZoneInfo, locale: str) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for entry in entries:
        local = entry.recorded_at.astimezone(zone)
        goals = []
        for link in entry.goal_links:
            label = resolve_label(link.goal.labels, locale)
            goals.append(f"{label} ({link.amount})" if link.amount is not None else label)
        writer.writerow(
            (
                local.date().isoformat(),
                local.strftime("%H:%M"),
                entry.score,
                entry.note or "",
                "; ".join(resolve_label(link.tag.labels, locale) for link in entry.tag_links),
                "; ".join(goals),
                "yes" if entry.is_favorite else "",
                sum(1 for item in entry.attachments if item.kind.value == "photo"),
                sum(1 for item in entry.attachments if item.kind.value == "audio"),
            )
        )
    # BOM so Excel opens Cyrillic text correctly.
    return "﻿" + buffer.getvalue()


# Zip headers and the central directory cost ~150 bytes per file; keep a generous margin.
_PER_FILE_OVERHEAD = 1024
# Room kept in part 1 for diary.json and entries.csv on top of their measured size.
_TEXT_SLACK_BYTES = 64 * 1024


def _new_part() -> IO[bytes]:
    return SpooledTemporaryFile(max_size=_SPOOL_MAX_BYTES)  # noqa: SIM115


def build_account_export_parts(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    locale: str,
    max_part_bytes: int | None = None,
    now: datetime | None = None,
) -> list[IO[bytes]]:
    """Build the export as one or more standalone ZIP files, each rewound to the start.

    Part 1 always holds ``diary.json`` and ``entries.csv``; photos and voice notes fill
    part 1 and then spill into further parts so no part grows past ``max_part_bytes``
    (a single file bigger than that still gets a part of its own). Every attachment
    in ``diary.json`` names the part that carries it.
    """
    exported_at = now or datetime.now(UTC)
    entries = _load_entries(db, user.id)
    base = DiaryArchive(
        exported_at=exported_at,
        account=ArchiveAccount(
            email=user.email,
            timezone=user.timezone,
            created_at=user.created_at,
            theme_preference=user.theme_preference,
            telegram_linked=user.telegram_linked,
        ),
        tag_groups=_tag_groups_payload(db, user.id),
        goals=_goals_payload(db, user.id),
        note_templates=_note_templates_payload(db, user.id),
        reminders=_reminders_payload(db, user.id),
        weights=_weights_payload(db, user.id),
        food=_food_payload(db, user.id),
        sleep=_sleep_payload(db, user.id),
    )
    entries_csv = _entries_csv(entries, zone=_user_zone(user), locale=locale)

    def render_json(files: dict[uuid.UUID, str | None], parts: dict[uuid.UUID, int]) -> str:
        archive = base.model_copy(
            update={"entries": [_entry_payload(entry, files, parts) for entry in entries]}
        )
        return json.dumps(archive.model_dump(mode="json"), ensure_ascii=False, indent=2)

    limit = max_part_bytes if max_part_bytes is not None else float("inf")
    # Worst-case text size: every attachment present and placed in a multi-digit part.
    all_files: dict[uuid.UUID, str | None] = {
        attachment.id: _attachment_path(attachment)
        for entry in entries
        for attachment in entry.attachments
    }
    worst_parts = dict.fromkeys(all_files, 999)
    text_reserve = (
        len(render_json(all_files, worst_parts).encode())
        + len(entries_csv.encode())
        + _TEXT_SLACK_BYTES
    )

    outputs = [_new_part()]
    first = zipfile.ZipFile(outputs[0], "w", compression=zipfile.ZIP_DEFLATED)
    current = first
    used = text_reserve
    files: dict[uuid.UUID, str | None] = {}
    parts: dict[uuid.UUID, int] = {}
    try:
        for entry in entries:
            for attachment in entry.attachments:
                try:
                    data = storage.get_object(key=attachment.storage_key)
                except StorageError:
                    # A lost object must not block the rest of the export.
                    files[attachment.id] = None
                    continue
                cost = len(data) + _PER_FILE_OVERHEAD
                part_has_files = used > (text_reserve if current is first else 0)
                if used + cost > limit and part_has_files:
                    if current is not first:
                        current.close()
                    outputs.append(_new_part())
                    current = zipfile.ZipFile(outputs[-1], "w")
                    used = 0
                path = _attachment_path(attachment)
                # Photos and audio are already compressed.
                current.writestr(path, data, compress_type=zipfile.ZIP_STORED)
                used += cost
                files[attachment.id] = path
                parts[attachment.id] = len(outputs)
        if current is not first:
            current.close()
        first.writestr("diary.json", render_json(files, parts))
        first.writestr("entries.csv", entries_csv)
    finally:
        first.close()
        if current is not first:
            current.close()

    for output in outputs:
        output.seek(0)
    return outputs


def build_account_export(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    locale: str,
    now: datetime | None = None,
) -> IO[bytes]:
    """Write the whole export into one ZIP and return it rewound to the start."""
    (archive,) = build_account_export_parts(db, user=user, storage=storage, locale=locale, now=now)
    return archive


def iter_file(handle: IO[bytes]) -> Iterator[bytes]:
    try:
        while chunk := handle.read(_CHUNK_BYTES):
            yield chunk
    finally:
        handle.close()


def export_filename(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
    return f"glowpath-export-{stamp}.zip"


def send_account_export_to_telegram(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    locale: str,
    now: datetime | None = None,
) -> int:
    """Have the bot send the export into the user's chat; return the number of files sent."""
    ensure_can_deliver(user)
    stamp = now or datetime.now(UTC)
    archives = build_account_export_parts(
        db,
        user=user,
        storage=storage,
        locale=locale,
        max_part_bytes=TELEGRAM_PART_BYTES,
        now=stamp,
    )
    total = len(archives)
    single_caption, part_caption = _TELEGRAM_CAPTIONS.get(locale, _TELEGRAM_CAPTIONS["en"])
    base_name = export_filename(stamp).removesuffix(".zip")
    try:
        for index, archive in enumerate(archives, start=1):
            if total == 1:
                filename, caption = f"{base_name}.zip", single_caption
            else:
                filename = f"{base_name}-part{index}of{total}.zip"
                caption = part_caption.format(part=index, total=total)
            send_to_user_chat(
                user=user,
                method="sendDocument",
                field="document",
                filename=filename,
                data=archive.read(),
                content_type="application/zip",
                caption=caption,
                timeout=_TELEGRAM_UPLOAD_TIMEOUT,
            )
    finally:
        for archive in archives:
            archive.close()
    return total
