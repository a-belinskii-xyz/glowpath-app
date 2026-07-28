from __future__ import annotations

import contextlib
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.mood_scale import MoodScore
from app.models.user_mood_icon import UserMoodIcon
from app.services.mood_entry_service import ALLOWED_PHOTO_MIME_TYPES
from app.services.mood_preferences_service import (
    get_or_create_preferences,
    reset_score_to_default_emoji,
    set_upload_icon_preference,
)
from app.services.storage import ObjectStorage, StorageError

MAX_MOOD_ICON_BYTES = 512 * 1024
MAX_MOOD_ICON_SOURCE_BYTES = 20 * 1024 * 1024
MAX_ICONS_PER_SCORE = 3
_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.ASCII)


class MoodIconError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _build_mood_icon_storage_key(
    *,
    user_id: uuid.UUID,
    score: int,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/mood-icons/{score}/{icon_id}_{_safe_filename(original_name)}"


def _build_mood_icon_source_storage_key(
    *,
    user_id: uuid.UUID,
    score: int,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/mood-icons/{score}/{icon_id}_source_{_safe_filename(original_name)}"


def _validate_image_payload(
    *,
    data: bytes,
    content_type: str,
    max_bytes: int,
    limit_label: str,
) -> str:
    mime_type = content_type.split(";")[0].strip().lower()
    if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise MoodIconError("Unsupported image MIME type")
    if len(data) > max_bytes:
        raise MoodIconError(f"Icon exceeds {limit_label} limit")
    return mime_type


def get_owned_icon(db: Session, *, user_id: uuid.UUID, icon_id: uuid.UUID) -> UserMoodIcon:
    icon = db.scalar(
        select(UserMoodIcon).where(
            UserMoodIcon.id == icon_id,
            UserMoodIcon.user_id == user_id,
        )
    )
    if icon is None:
        raise MoodIconError("Mood icon not found", status_code=404)
    return icon


def count_icons_for_score(db: Session, *, user_id: uuid.UUID, score: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserMoodIcon)
            .where(
                UserMoodIcon.user_id == user_id,
                UserMoodIcon.score == score,
            )
        )
        or 0
    )


def list_mood_icons(
    db: Session,
    *,
    user_id: uuid.UUID,
    score: int | None = None,
) -> list[UserMoodIcon]:
    query = select(UserMoodIcon).where(UserMoodIcon.user_id == user_id)
    if score is not None:
        try:
            MoodScore(score)
        except ValueError as exc:
            raise MoodIconError("Score must be between 1 and 5") from exc
        query = query.where(UserMoodIcon.score == score)
    query = query.order_by(UserMoodIcon.score.asc(), UserMoodIcon.created_at.asc())
    return list(db.scalars(query).all())


def upload_mood_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    score: int,
    data: bytes,
    content_type: str,
    original_name: str,
    storage: ObjectStorage,
    source_data: bytes | None = None,
    source_content_type: str | None = None,
    source_original_name: str | None = None,
) -> UserMoodIcon:
    try:
        mood_score = MoodScore(score)
    except ValueError as exc:
        raise MoodIconError("Score must be between 1 and 5") from exc

    mime_type = _validate_image_payload(
        data=data,
        content_type=content_type,
        max_bytes=MAX_MOOD_ICON_BYTES,
        limit_label="512 KB",
    )
    size_bytes = len(data)
    if count_icons_for_score(db, user_id=user_id, score=score) >= MAX_ICONS_PER_SCORE:
        raise MoodIconError(
            f"At most {MAX_ICONS_PER_SCORE} uploaded icons are allowed per mood score"
        )

    source_mime_type: str | None = None
    source_size_bytes: int | None = None
    source_storage_key: str | None = None
    if source_data is not None:
        source_mime_type = _validate_image_payload(
            data=source_data,
            content_type=source_content_type or "application/octet-stream",
            max_bytes=MAX_MOOD_ICON_SOURCE_BYTES,
            limit_label="20 MB",
        )
        source_size_bytes = len(source_data)

    icon_id = uuid.uuid4()
    storage_key = _build_mood_icon_storage_key(
        user_id=user_id,
        score=score,
        icon_id=icon_id,
        original_name=original_name,
    )
    storage.put_object(key=storage_key, data=data, content_type=mime_type)

    if source_data is not None and source_mime_type is not None:
        source_storage_key = _build_mood_icon_source_storage_key(
            user_id=user_id,
            score=score,
            icon_id=icon_id,
            original_name=source_original_name or original_name,
        )
        try:
            storage.put_object(
                key=source_storage_key,
                data=source_data,
                content_type=source_mime_type,
            )
        except Exception:
            with contextlib.suppress(StorageError):
                storage.delete_object(key=storage_key)
            raise

    icon = UserMoodIcon(
        id=icon_id,
        user_id=user_id,
        score=score,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        original_name=original_name[:255],
        source_storage_key=source_storage_key,
        source_mime_type=source_mime_type,
        source_size_bytes=source_size_bytes,
    )
    db.add(icon)

    try:
        set_upload_icon_preference(db, user_id=user_id, score=mood_score, icon_id=icon.id)
        db.commit()
    except Exception:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=storage_key)
        if source_storage_key is not None:
            with contextlib.suppress(StorageError):
                storage.delete_object(key=source_storage_key)
        raise

    db.refresh(icon)
    return icon


def download_mood_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserMoodIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    data = storage.get_object(key=icon.storage_key)
    return icon, data


def download_mood_icon_source(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserMoodIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    if not icon.source_storage_key or not icon.source_mime_type:
        raise MoodIconError("Mood icon source not found", status_code=404)
    data = storage.get_object(key=icon.source_storage_key)
    return icon, data


def delete_mood_icon_by_id(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    mood_score = MoodScore(icon.score)
    storage_key = icon.storage_key
    source_storage_key = icon.source_storage_key
    remaining = [
        row for row in list_mood_icons(db, user_id=user_id, score=icon.score) if row.id != icon.id
    ]

    prefs = get_or_create_preferences(db, user_id=user_id)
    current = (prefs.score_styles or {}).get(str(mood_score.value), {})
    is_active = current.get("icon_type") == "upload" and str(current.get("icon")) == str(icon.id)

    db.delete(icon)
    if is_active:
        if remaining:
            set_upload_icon_preference(
                db,
                user_id=user_id,
                score=mood_score,
                icon_id=remaining[-1].id,
            )
        else:
            reset_score_to_default_emoji(db, user_id=user_id, score=mood_score)
    db.commit()

    with contextlib.suppress(StorageError):
        storage.delete_object(key=storage_key)
    if source_storage_key:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=source_storage_key)
