from __future__ import annotations

import contextlib
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.goal import (
    DEFAULT_GOAL_ICON,
    DEFAULT_GOAL_ICON_TYPE,
    Goal,
)
from app.models.user_goal_icon import UserGoalIcon
from app.services.goal_service import get_goal
from app.services.mood_entry_service import ALLOWED_PHOTO_MIME_TYPES
from app.services.storage import ObjectStorage, StorageError

MAX_GOAL_ICON_BYTES = 512 * 1024
MAX_GOAL_ICON_SOURCE_BYTES = 20 * 1024 * 1024
MAX_ICONS_PER_GOAL = 3
_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-]+", re.ASCII)


class GoalIconError(AppError):
    pass


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME_RE.sub("_", name.strip()).strip("._")
    if not cleaned:
        return "file"
    return cleaned[:200]


def _build_goal_icon_storage_key(
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/goal-icons/{goal_id}/{icon_id}_{_safe_filename(original_name)}"


def _build_goal_icon_source_storage_key(
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    icon_id: uuid.UUID,
    original_name: str,
) -> str:
    return f"{user_id}/goal-icons/{goal_id}/{icon_id}_source_{_safe_filename(original_name)}"


def _validate_image_payload(
    *,
    data: bytes,
    content_type: str,
    max_bytes: int,
    limit_label: str,
) -> str:
    mime_type = content_type.split(";")[0].strip().lower()
    if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise GoalIconError("Unsupported image MIME type", code="unsupported_image_mime")
    if len(data) > max_bytes:
        raise GoalIconError(
            f"Icon exceeds {limit_label} limit",
            code="icon_too_large",
            params={"limit": limit_label},
        )
    return mime_type


def get_owned_icon(db: Session, *, user_id: uuid.UUID, icon_id: uuid.UUID) -> UserGoalIcon:
    icon = db.scalar(
        select(UserGoalIcon).where(
            UserGoalIcon.id == icon_id,
            UserGoalIcon.user_id == user_id,
        )
    )
    if icon is None:
        raise GoalIconError("Goal icon not found", code="goal_icon_not_found", status_code=404)
    return icon


def count_icons_for_goal(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserGoalIcon)
            .where(
                UserGoalIcon.user_id == user_id,
                UserGoalIcon.goal_id == goal_id,
            )
        )
        or 0
    )


def list_goal_icons(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> list[UserGoalIcon]:
    get_goal(db, user_id=user_id, goal_id=goal_id)
    return list(
        db.scalars(
            select(UserGoalIcon)
            .where(
                UserGoalIcon.user_id == user_id,
                UserGoalIcon.goal_id == goal_id,
            )
            .order_by(UserGoalIcon.created_at.asc())
        ).all()
    )


def set_upload_icon_on_goal(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    icon_id: uuid.UUID,
) -> Goal:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    goal.icon_type = "upload"
    goal.icon = str(icon_id)
    return goal


def reset_goal_to_default_emoji(db: Session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> Goal:
    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    goal.icon_type = DEFAULT_GOAL_ICON_TYPE
    goal.icon = DEFAULT_GOAL_ICON
    return goal


def upload_goal_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    data: bytes,
    content_type: str,
    original_name: str,
    storage: ObjectStorage,
    source_data: bytes | None = None,
    source_content_type: str | None = None,
    source_original_name: str | None = None,
) -> tuple[UserGoalIcon, Goal]:
    get_goal(db, user_id=user_id, goal_id=goal_id)

    mime_type = _validate_image_payload(
        data=data,
        content_type=content_type,
        max_bytes=MAX_GOAL_ICON_BYTES,
        limit_label="512 KB",
    )
    size_bytes = len(data)
    if count_icons_for_goal(db, user_id=user_id, goal_id=goal_id) >= MAX_ICONS_PER_GOAL:
        raise GoalIconError(
            f"At most {MAX_ICONS_PER_GOAL} uploaded icons are allowed per goal",
            code="goal_icon_limit",
            params={"max": str(MAX_ICONS_PER_GOAL)},
        )

    source_mime_type: str | None = None
    source_size_bytes: int | None = None
    source_storage_key: str | None = None
    if source_data is not None:
        source_mime_type = _validate_image_payload(
            data=source_data,
            content_type=source_content_type or "application/octet-stream",
            max_bytes=MAX_GOAL_ICON_SOURCE_BYTES,
            limit_label="20 MB",
        )
        source_size_bytes = len(source_data)

    icon_id = uuid.uuid4()
    storage_key = _build_goal_icon_storage_key(
        user_id=user_id,
        goal_id=goal_id,
        icon_id=icon_id,
        original_name=original_name,
    )
    storage.put_object(key=storage_key, data=data, content_type=mime_type)

    if source_data is not None and source_mime_type is not None:
        source_storage_key = _build_goal_icon_source_storage_key(
            user_id=user_id,
            goal_id=goal_id,
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

    icon = UserGoalIcon(
        id=icon_id,
        user_id=user_id,
        goal_id=goal_id,
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
        goal = set_upload_icon_on_goal(db, user_id=user_id, goal_id=goal_id, icon_id=icon.id)
        db.commit()
    except Exception:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=storage_key)
        if source_storage_key is not None:
            with contextlib.suppress(StorageError):
                storage.delete_object(key=source_storage_key)
        raise

    db.refresh(icon)
    db.refresh(goal)
    return icon, goal


def download_goal_icon(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserGoalIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    data = storage.get_object(key=icon.storage_key)
    return icon, data


def download_goal_icon_source(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[UserGoalIcon, bytes]:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    if not icon.source_storage_key or not icon.source_mime_type:
        raise GoalIconError(
            "Goal icon source not found", code="goal_icon_source_not_found", status_code=404
        )
    data = storage.get_object(key=icon.source_storage_key)
    return icon, data


def delete_goal_icon_by_id(
    db: Session,
    *,
    user_id: uuid.UUID,
    icon_id: uuid.UUID,
    storage: ObjectStorage,
) -> Goal:
    icon = get_owned_icon(db, user_id=user_id, icon_id=icon_id)
    goal_id = icon.goal_id
    storage_key = icon.storage_key
    source_storage_key = icon.source_storage_key
    remaining = [
        row for row in list_goal_icons(db, user_id=user_id, goal_id=goal_id) if row.id != icon.id
    ]

    goal = get_goal(db, user_id=user_id, goal_id=goal_id)
    is_active = goal.icon_type == "upload" and goal.icon == str(icon.id)

    db.delete(icon)
    if is_active:
        if remaining:
            set_upload_icon_on_goal(
                db,
                user_id=user_id,
                goal_id=goal_id,
                icon_id=remaining[-1].id,
            )
        else:
            reset_goal_to_default_emoji(db, user_id=user_id, goal_id=goal_id)
    db.commit()

    with contextlib.suppress(StorageError):
        storage.delete_object(key=storage_key)
    if source_storage_key:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=source_storage_key)

    return get_goal(db, user_id=user_id, goal_id=goal_id)
