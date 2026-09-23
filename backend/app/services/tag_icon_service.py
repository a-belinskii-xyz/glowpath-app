from __future__ import annotations

import contextlib
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.default_tag_groups import DEFAULT_TAG_ICON, DEFAULT_TAG_ICON_TYPE
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.tag import Tag
from app.models.user_tag_icon import UserTagIcon
from app.services.mood_entry_service import ALLOWED_PHOTO_MIME_TYPES
from app.services.storage import ObjectStorage, StorageError
from app.services.tag_service import get_owned_tag

MAX_TAG_ICON_BYTES = 512 * 1024
MAX_TAG_ICON_SOURCE_BYTES = 20 * 1024 * 1024
MAX_ICONS_PER_TAG = 3
_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.ASCII)


class TagIconError(AppError):
    pass


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _build_tag_icon_storage_key(
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/tag-icons/{tag_id}/{icon_id}_{_safe_filename(original_name)}"


def _build_tag_icon_source_storage_key(
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/tag-icons/{tag_id}/{icon_id}_source_{_safe_filename(original_name)}"


def _validate_image_payload(
    *,
    data: bytes,
    content_type: str,
    max_bytes: int,
    limit_label: str,
) -> str:
    mime_type = content_type.split(";")[0].strip().lower()
    if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise TagIconError("Unsupported image MIME type", code=ErrorCode.UNSUPPORTED_IMAGE_MIME)
    if len(data) > max_bytes:
        raise TagIconError(
            f"Icon exceeds {limit_label} limit",
            code=ErrorCode.ICON_TOO_LARGE,
            params={"limit": limit_label},
        )
    return mime_type


def get_owned_icon(db: Session, *, user_id: uuid.UUID, icon_id: uuid.UUID) -> UserTagIcon:
    icon = db.scalar(
        select(UserTagIcon).where(
            UserTagIcon.id == icon_id,
            UserTagIcon.user_id == user_id,
        )
    )
    if icon is None:
        raise TagIconError("Tag icon not found", code=ErrorCode.TAG_ICON_NOT_FOUND, status_code=404)
    return icon


def count_icons_for_tag(db: Session, *, user_id: uuid.UUID, tag_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserTagIcon)
            .where(
                UserTagIcon.user_id == user_id,
                UserTagIcon.tag_id == tag_id,
            )
        )
        or 0
    )


def list_tag_icons(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> list[UserTagIcon]:
    get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    return list(
        db.scalars(
            select(UserTagIcon)
            .where(
                UserTagIcon.user_id == user_id,
                UserTagIcon.tag_id == tag_id,
            )
            .order_by(UserTagIcon.created_at.asc())
        ).all()
    )


def set_upload_icon_on_tag(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    icon_id: uuid.UUID,
) -> Tag:
    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    tag.icon_type = "upload"
    tag.icon = str(icon_id)
    return tag


def reset_tag_to_default_emoji(db: Session, *, user_id: uuid.UUID, tag_id: uuid.UUID) -> Tag:
    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    tag.icon_type = DEFAULT_TAG_ICON_TYPE
    tag.icon = DEFAULT_TAG_ICON
    return tag


def upload_tag_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    data: bytes,
    content_type: str,
    original_name: str,
    storage: ObjectStorage,
    source_data: bytes | None = None,
    source_content_type: str | None = None,
    source_original_name: str | None = None,
) -> tuple[UserTagIcon, Tag]:
    get_owned_tag(db, user_id=user_id, tag_id=tag_id)

    mime_type = _validate_image_payload(
        data=data,
        content_type=content_type,
        max_bytes=MAX_TAG_ICON_BYTES,
        limit_label="512 KB",
    )
    size_bytes = len(data)
    if count_icons_for_tag(db, user_id=user_id, tag_id=tag_id) >= MAX_ICONS_PER_TAG:
        raise TagIconError(
            f"At most {MAX_ICONS_PER_TAG} uploaded icons are allowed per tag",
            code=ErrorCode.TAG_ICON_LIMIT,
            params={"max": str(MAX_ICONS_PER_TAG)},
        )

    source_mime_type: str | None = None
    source_size_bytes: int | None = None
    source_storage_key: str | None = None
    if source_data is not None:
        source_mime_type = _validate_image_payload(
            data=source_data,
            content_type=source_content_type or "application/octet-stream",
            max_bytes=MAX_TAG_ICON_SOURCE_BYTES,
            limit_label="20 MB",
        )
        source_size_bytes = len(source_data)

    icon_id = uuid.uuid4()
    storage_key = _build_tag_icon_storage_key(
        user_id=user_id,
        tag_id=tag_id,
        icon_id=icon_id,
        original_name=original_name,
    )
    storage.put_object(key=storage_key, data=data, content_type=mime_type)

    if source_data is not None and source_mime_type is not None:
        source_storage_key = _build_tag_icon_source_storage_key(
            user_id=user_id,
            tag_id=tag_id,
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

    icon = UserTagIcon(
        id=icon_id,
        user_id=user_id,
        tag_id=tag_id,
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
        tag = set_upload_icon_on_tag(db, user_id=user_id, tag_id=tag_id, icon_id=icon.id)
        db.commit()
    except Exception:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=storage_key)
        if source_storage_key is not None:
            with contextlib.suppress(StorageError):
                storage.delete_object(key=source_storage_key)
        raise

    db.refresh(icon)
    db.refresh(tag)
    return icon, tag


def download_tag_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserTagIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    data = storage.get_object(key=icon.storage_key)
    return icon, data


def download_tag_icon_source(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserTagIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    if not icon.source_storage_key or not icon.source_mime_type:
        raise TagIconError(
            "Tag icon source not found", code=ErrorCode.TAG_ICON_SOURCE_NOT_FOUND, status_code=404
        )
    data = storage.get_object(key=icon.source_storage_key)
    return icon, data


def delete_tag_icon_by_id(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> Tag:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    tag_id = icon.tag_id
    storage_key = icon.storage_key
    source_storage_key = icon.source_storage_key
    remaining = [
        row for row in list_tag_icons(db, user_id=user_id, tag_id=tag_id) if row.id != icon.id
    ]

    tag = get_owned_tag(db, user_id=user_id, tag_id=tag_id)
    is_active = tag.icon_type == "upload" and tag.icon == str(icon.id)

    db.delete(icon)
    if is_active:
        if remaining:
            set_upload_icon_on_tag(
                db,
                user_id=user_id,
                tag_id=tag_id,
                icon_id=remaining[-1].id,
            )
        else:
            reset_tag_to_default_emoji(db, user_id=user_id, tag_id=tag_id)
    db.commit()

    with contextlib.suppress(StorageError):
        storage.delete_object(key=storage_key)
    if source_storage_key:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=source_storage_key)

    return get_owned_tag(db, user_id=user_id, tag_id=tag_id)
