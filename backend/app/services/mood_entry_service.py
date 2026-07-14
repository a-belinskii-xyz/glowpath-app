from __future__ import annotations

import contextlib
import re
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.attachment_kind import AttachmentKind
from app.core.i18n import resolve_label
from app.core.mood_scale import (
    MAX_MOOD_SCORE,
    MIN_MOOD_SCORE,
    MoodScore,
    mood_score_emoji,
    mood_score_label,
)
from app.models.mood_entry import MoodEntry
from app.models.mood_entry_attachment import MAX_PHOTOS_PER_ENTRY, MoodEntryAttachment
from app.models.mood_entry_tag import MoodEntryTag
from app.models.tag import Tag
from app.services.storage import ObjectStorage, StorageError

CALENDAR_SCORES_PER_DAY = 3

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024

ALLOWED_PHOTO_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
ALLOWED_AUDIO_MIME_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/webm",
        "audio/aac",
    }
)

_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.UNICODE)


class MoodEntryError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise MoodEntryError("recorded_at must include a timezone offset")
    return value.astimezone(UTC)


def _entry_load_options() -> tuple[Any, ...]:
    return (
        selectinload(MoodEntry.tag_links).selectinload(MoodEntryTag.tag),
        selectinload(MoodEntry.attachments),
    )


def _get_owned_entry(db: Session, *, user_id: uuid.UUID, entry_id: uuid.UUID) -> MoodEntry:
    entry = db.scalar(
        select(MoodEntry)
        .options(*_entry_load_options())
        .where(MoodEntry.id == entry_id, MoodEntry.user_id == user_id)
    )
    if entry is None:
        raise MoodEntryError("Mood entry not found", status_code=404)
    return entry


def _resolve_user_tags(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> list[Tag]:
    if not tag_ids:
        return []

    unique_ids = list(dict.fromkeys(tag_ids))
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user_id, Tag.id.in_(unique_ids))).all())
    if len(tags) != len(unique_ids):
        raise MoodEntryError("One or more tags were not found", status_code=400)
    return tags


def _replace_entry_tags(db: Session, entry: MoodEntry, tags: list[Tag]) -> None:
    entry.tag_links.clear()
    db.flush()
    for tag in tags:
        entry.tag_links.append(MoodEntryTag(tag_id=tag.id))


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _build_storage_key(
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/{entry_id}/{attachment_id}_{_safe_filename(original_name)}"


def _next_photo_position(attachments: list[MoodEntryAttachment]) -> int:
    used = {item.position for item in attachments if item.kind == AttachmentKind.PHOTO}
    for position in range(1, MAX_PHOTOS_PER_ENTRY + 1):
        if position not in used:
            return position
    raise MoodEntryError("Photo limit reached for this entry", status_code=409)


def create_mood_entry(
    db: Session,
    *,
    user_id: uuid.UUID,
    score: int,
    recorded_at: datetime,
    note: str | None,
    tag_ids: list[uuid.UUID],
) -> MoodEntry:
    tags = _resolve_user_tags(db, user_id=user_id, tag_ids=tag_ids)
    entry = MoodEntry(
        user_id=user_id,
        score=score,
        recorded_at=_to_utc(recorded_at),
        note=note,
    )
    db.add(entry)
    db.flush()
    _replace_entry_tags(db, entry, tags)
    db.commit()
    return _get_owned_entry(db, user_id=user_id, entry_id=entry.id)


def list_mood_entries(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
    recorded_from: datetime | None = None,
    recorded_to: datetime | None = None,
) -> list[MoodEntry]:
    stmt = select(MoodEntry).options(*_entry_load_options()).where(MoodEntry.user_id == user_id)
    if recorded_from is not None:
        stmt = stmt.where(MoodEntry.recorded_at >= _to_utc(recorded_from))
    if recorded_to is not None:
        stmt = stmt.where(MoodEntry.recorded_at < _to_utc(recorded_to))
    return list(
        db.scalars(
            stmt.order_by(MoodEntry.recorded_at.desc(), MoodEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def _resolve_user_tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise MoodEntryError(f"Unknown timezone: {timezone_name}", status_code=400) from exc


def _local_date(recorded_at: datetime, tz: ZoneInfo) -> date:
    instant = recorded_at if recorded_at.tzinfo is not None else recorded_at.replace(tzinfo=UTC)
    return instant.astimezone(tz).date()


def get_mood_entry_calendar(
    db: Session,
    *,
    user_id: uuid.UUID,
    timezone_name: str,
    recorded_from: datetime,
    recorded_to: datetime,
) -> list[dict[str, Any]]:
    """Return per-day mood scores for a range, grouped in the user's timezone.

    Each day includes up to ``CALENDAR_SCORES_PER_DAY`` most recent scores
    (newest first) plus the total entry count for that day.
    """
    tz = _resolve_user_tz(timezone_name)
    from_utc = _to_utc(recorded_from)
    to_utc = _to_utc(recorded_to)
    if to_utc <= from_utc:
        raise MoodEntryError("recorded_to must be after recorded_from")

    rows = list(
        db.execute(
            select(MoodEntry.recorded_at, MoodEntry.score)
            .where(
                MoodEntry.user_id == user_id,
                MoodEntry.recorded_at >= from_utc,
                MoodEntry.recorded_at < to_utc,
            )
            .order_by(MoodEntry.recorded_at.desc(), MoodEntry.created_at.desc())
        ).all()
    )

    by_day: dict[date, list[int]] = defaultdict(list)
    for recorded_at, score in rows:
        by_day[_local_date(recorded_at, tz)].append(int(score))

    days: list[dict[str, Any]] = []
    for day in sorted(by_day.keys()):
        scores = by_day[day]
        days.append(
            {
                "date": day.isoformat(),
                "entry_count": len(scores),
                "scores": [
                    {
                        "score": score,
                        "score_emoji": mood_score_emoji(MoodScore(score)),
                    }
                    for score in scores[:CALENDAR_SCORES_PER_DAY]
                ],
            }
        )
    return days


def get_mood_entry_stats(
    db: Session,
    *,
    user_id: uuid.UUID,
    recorded_from: datetime,
    recorded_to: datetime,
    locale: str,
) -> dict[str, Any]:
    """Return per-score entry counts for a recorded_at range.

    Always includes all scores from ``MIN_MOOD_SCORE`` to ``MAX_MOOD_SCORE``
    (count may be zero) so charts have a stable axis.
    """
    from_utc = _to_utc(recorded_from)
    to_utc = _to_utc(recorded_to)
    if to_utc <= from_utc:
        raise MoodEntryError("recorded_to must be after recorded_from")

    rows = db.execute(
        select(MoodEntry.score, func.count())
        .where(
            MoodEntry.user_id == user_id,
            MoodEntry.recorded_at >= from_utc,
            MoodEntry.recorded_at < to_utc,
        )
        .group_by(MoodEntry.score)
    ).all()
    counts = {int(score): int(count) for score, count in rows}

    scores: list[dict[str, Any]] = []
    total_entries = 0
    for value in range(MIN_MOOD_SCORE, MAX_MOOD_SCORE + 1):
        count = counts.get(value, 0)
        total_entries += count
        mood = MoodScore(value)
        scores.append(
            {
                "score": value,
                "score_label": mood_score_label(mood, locale),
                "score_emoji": mood_score_emoji(mood),
                "count": count,
            }
        )

    return {"total_entries": total_entries, "scores": scores}


def get_mood_entry(db: Session, *, user_id: uuid.UUID, entry_id: uuid.UUID) -> MoodEntry:
    return _get_owned_entry(db, user_id=user_id, entry_id=entry_id)


def patch_mood_entry(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    fields: dict[str, Any],
) -> MoodEntry:
    entry = _get_owned_entry(db, user_id=user_id, entry_id=entry_id)

    if "score" in fields and fields["score"] is not None:
        entry.score = fields["score"]
    if "recorded_at" in fields and fields["recorded_at"] is not None:
        entry.recorded_at = _to_utc(fields["recorded_at"])
    if "note" in fields:
        entry.note = fields["note"]
    if "tag_ids" in fields:
        tags = _resolve_user_tags(db, user_id=user_id, tag_ids=fields["tag_ids"] or [])
        _replace_entry_tags(db, entry, tags)

    db.commit()
    return _get_owned_entry(db, user_id=user_id, entry_id=entry_id)


def delete_mood_entry(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    entry = _get_owned_entry(db, user_id=user_id, entry_id=entry_id)
    storage_keys = [attachment.storage_key for attachment in entry.attachments]
    db.delete(entry)
    db.commit()
    for key in storage_keys:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=key)


def upload_attachment(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    kind: AttachmentKind,
    data: bytes,
    content_type: str,
    original_name: str,
    storage: ObjectStorage,
) -> MoodEntryAttachment:
    entry = _get_owned_entry(db, user_id=user_id, entry_id=entry_id)
    mime_type = content_type.split(";")[0].strip().lower()
    size_bytes = len(data)

    if kind == AttachmentKind.PHOTO:
        if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
            raise MoodEntryError("Unsupported photo MIME type")
        if size_bytes > MAX_PHOTO_BYTES:
            raise MoodEntryError("Photo exceeds 5 MB limit")
        if sum(1 for item in entry.attachments if item.kind == AttachmentKind.PHOTO) >= (
            MAX_PHOTOS_PER_ENTRY
        ):
            raise MoodEntryError("Photo limit reached for this entry", status_code=409)
        position = _next_photo_position(entry.attachments)
    elif kind == AttachmentKind.AUDIO:
        if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
            raise MoodEntryError("Unsupported audio MIME type")
        if size_bytes > MAX_AUDIO_BYTES:
            raise MoodEntryError("Audio exceeds 10 MB limit")
        if any(item.kind == AttachmentKind.AUDIO for item in entry.attachments):
            raise MoodEntryError("Audio already exists for this entry", status_code=409)
        position = None
    else:
        raise MoodEntryError("Invalid attachment kind")

    attachment_id = uuid.uuid4()
    storage_key = _build_storage_key(
        user_id=user_id,
        entry_id=entry_id,
        attachment_id=attachment_id,
        original_name=original_name,
    )
    storage.put_object(key=storage_key, data=data, content_type=mime_type)

    attachment = MoodEntryAttachment(
        id=attachment_id,
        mood_entry_id=entry.id,
        kind=kind,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        original_name=original_name[:255],
        position=position,
    )
    db.add(attachment)
    try:
        db.commit()
    except Exception:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=storage_key)
        raise
    db.refresh(attachment)
    return attachment


def get_attachment(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> MoodEntryAttachment:
    entry = _get_owned_entry(db, user_id=user_id, entry_id=entry_id)
    for attachment in entry.attachments:
        if attachment.id == attachment_id:
            return attachment
    raise MoodEntryError("Attachment not found", status_code=404)


def download_attachment(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[MoodEntryAttachment, bytes]:
    attachment = get_attachment(
        db,
        user_id=user_id,
        entry_id=entry_id,
        attachment_id=attachment_id,
    )
    try:
        data = storage.get_object(key=attachment.storage_key)
    except StorageError as exc:
        raise MoodEntryError(exc.message, status_code=exc.status_code) from exc
    return attachment, data


def delete_attachment(
    db: Session,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    attachment = get_attachment(
        db,
        user_id=user_id,
        entry_id=entry_id,
        attachment_id=attachment_id,
    )
    storage_key = attachment.storage_key
    db.delete(attachment)
    db.commit()
    with contextlib.suppress(StorageError):
        storage.delete_object(key=storage_key)


def serialize_mood_entry(entry: MoodEntry, *, locale: str) -> dict[str, Any]:
    score = MoodScore(entry.score)
    tags = [
        {
            "id": link.tag.id,
            "slug": link.tag.slug,
            "label": resolve_label(link.tag.labels, locale),
            "group_id": link.tag.group_id,
        }
        for link in sorted(entry.tag_links, key=lambda item: item.tag.sort_order)
        if link.tag is not None
    ]
    attachments = [
        {
            "id": item.id,
            "kind": item.kind,
            "mime_type": item.mime_type,
            "size_bytes": item.size_bytes,
            "original_name": item.original_name,
            "position": item.position,
        }
        for item in sorted(
            entry.attachments,
            key=lambda item: (item.position is None, item.position or 0, item.created_at),
        )
    ]
    return {
        "id": entry.id,
        "recorded_at": entry.recorded_at,
        "score": entry.score,
        "score_label": mood_score_label(score, locale),
        "score_emoji": mood_score_emoji(score),
        "note": entry.note,
        "tags": tags,
        "attachments": attachments,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
