"""Full personal-data export: one ZIP with JSON, CSV and attachment files."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
import uuid
import zipfile
from collections.abc import Iterator
from datetime import UTC, date, datetime
from tempfile import SpooledTemporaryFile
from typing import IO, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.i18n import resolve_label
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MoodEntryAttachment
from app.models.mood_entry_goal import MoodEntryGoal
from app.models.mood_entry_tag import MoodEntryTag
from app.models.note_template import NoteTemplate
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.storage import ObjectStorage, StorageError

EXPORT_FORMAT_VERSION = 1
# Small exports stay in memory; bigger ones (many photos) spill to a temp file.
_SPOOL_MAX_BYTES = 16 * 1024 * 1024
_CHUNK_BYTES = 64 * 1024

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


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


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
                selectinload(MoodEntry.tag_links).selectinload(MoodEntryTag.tag),
                selectinload(MoodEntry.goal_links).selectinload(MoodEntryGoal.goal),
                selectinload(MoodEntry.attachments),
            )
            .order_by(MoodEntry.recorded_at, MoodEntry.id)
        )
    )


def _tag_groups_payload(db: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    groups = db.scalars(
        select(TagGroup)
        .where(TagGroup.user_id == user_id)
        .options(selectinload(TagGroup.tags))
        .order_by(TagGroup.sort_order, TagGroup.created_at)
    )
    return [
        {
            "slug": group.slug,
            "labels": group.labels,
            "show_on_entry": group.show_on_entry,
            "tags": [
                {"slug": tag.slug, "labels": tag.labels, "color": tag.color}
                for tag in sorted(group.tags, key=lambda item: (item.sort_order, item.slug))
            ],
        }
        for group in groups
    ]


def _goals_payload(db: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    goals = db.scalars(
        select(Goal).where(Goal.user_id == user_id).order_by(Goal.sort_order, Goal.created_at)
    )
    return [
        {
            "slug": goal.slug,
            "labels": goal.labels,
            "tracking_kind": goal.tracking_kind,
            "times_per_week": goal.times_per_week,
            "target_amount": goal.target_amount,
            "unit": goal.unit,
            "starts_on": _iso(goal.starts_on),
            "ends_on": _iso(goal.ends_on),
            "color": goal.color,
        }
        for goal in goals
    ]


def _note_templates_payload(db: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    templates = db.scalars(
        select(NoteTemplate)
        .where(NoteTemplate.user_id == user_id)
        .order_by(NoteTemplate.sort_order, NoteTemplate.created_at)
    )
    return [{"slug": item.slug, "labels": item.labels, "bodies": item.bodies} for item in templates]


def _reminders_payload(db: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    schedules = db.scalars(
        select(UserNotificationSchedule)
        .where(UserNotificationSchedule.user_id == user_id)
        .order_by(UserNotificationSchedule.kind)
    )
    return [
        {
            "kind": item.kind,
            "enabled": item.enabled,
            "time_of_day": item.time_of_day,
            "interval_days": item.interval_days,
            "days_of_week": item.days_of_week,
            "channels": item.channels,
        }
        for item in schedules
    ]


def _entry_payload(entry: MoodEntry, files: dict[uuid.UUID, str | None]) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "recorded_at": _iso(entry.recorded_at),
        "logged_on": _iso(entry.logged_on),
        "logged_timezone": entry.logged_timezone,
        "score": entry.score,
        "score_color": entry.score_color,
        "note": entry.note,
        "is_favorite": entry.is_favorite,
        "tags": [{"slug": link.tag.slug, "labels": link.tag.labels} for link in entry.tag_links],
        "goals": [
            {"slug": link.goal.slug, "labels": link.goal.labels, "amount": link.amount}
            for link in entry.goal_links
        ],
        "attachments": [
            {
                "kind": attachment.kind.value,
                "file": files.get(attachment.id),
                "mime_type": attachment.mime_type,
                "size_bytes": attachment.size_bytes,
                "original_name": attachment.original_name,
                "position": attachment.position,
                "transcription": attachment.transcription,
            }
            for attachment in sorted(
                entry.attachments, key=lambda item: (item.kind.value, item.position or 0)
            )
        ],
    }


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


def build_account_export(
    db: Session,
    *,
    user: User,
    storage: ObjectStorage,
    locale: str,
    now: datetime | None = None,
) -> IO[bytes]:
    """Write the export ZIP to a spooled temp file and return it rewound to the start."""
    exported_at = now or datetime.now(UTC)
    entries = _load_entries(db, user.id)
    output: IO[bytes] = SpooledTemporaryFile(max_size=_SPOOL_MAX_BYTES)  # noqa: SIM115

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        files: dict[uuid.UUID, str | None] = {}
        for entry in entries:
            for attachment in entry.attachments:
                try:
                    data = storage.get_object(key=attachment.storage_key)
                except StorageError:
                    # A lost object must not block the rest of the export.
                    files[attachment.id] = None
                    continue
                path = _attachment_path(attachment)
                # Photos and audio are already compressed.
                archive.writestr(path, data, compress_type=zipfile.ZIP_STORED)
                files[attachment.id] = path

        payload = {
            "format_version": EXPORT_FORMAT_VERSION,
            "exported_at": _iso(exported_at),
            "account": {
                "email": user.email,
                "timezone": user.timezone,
                "created_at": _iso(user.created_at),
                "theme_preference": user.theme_preference,
                "telegram_linked": user.telegram_linked,
            },
            "tag_groups": _tag_groups_payload(db, user.id),
            "goals": _goals_payload(db, user.id),
            "note_templates": _note_templates_payload(db, user.id),
            "reminders": _reminders_payload(db, user.id),
            "entries": [_entry_payload(entry, files) for entry in entries],
        }
        archive.writestr("diary.json", json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr("entries.csv", _entries_csv(entries, zone=_user_zone(user), locale=locale))

    output.seek(0)
    return output


def iter_file(handle: IO[bytes]) -> Iterator[bytes]:
    try:
        while chunk := handle.read(_CHUNK_BYTES):
            yield chunk
    finally:
        handle.close()


def export_filename(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
    return f"glowpath-export-{stamp}.zip"
