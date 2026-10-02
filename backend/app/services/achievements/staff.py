"""Staff editing of achievements: create, edit, archive, image icons."""

from __future__ import annotations

import contextlib
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.achievement_criteria import InvalidCriteriaError, normalize_criteria
from app.core.achievements import (
    ACHIEVEMENT_CATEGORIES,
    ACHIEVEMENT_STATUSES,
    ACHIEVEMENT_VISIBILITIES,
    DEFAULT_ACHIEVEMENT_ICON,
    AchievementIconType,
    AchievementRewardKind,
    AchievementStatus,
    AchievementVisibility,
)
from app.core.error_codes import ErrorCode
from app.core.i18n import resolve_label
from app.core.marketplace import ALLOWED_CATALOG_MIME_TYPES, MAX_CATALOG_ICON_BYTES
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.services.achievements.service import AchievementError
from app.services.storage import ObjectStorage, StorageError

_SLUG_RE = re.compile(r"[^a-z0-9]+")
MAX_ACHIEVEMENT_SLUG = 64
MAX_ACHIEVEMENT_EMOJI = 16


@dataclass(frozen=True, slots=True)
class RewardInput:
    kind: str
    amount: int | None = None
    pack_id: uuid.UUID | None = None
    catalog_icon_id: uuid.UUID | None = None


def _slugify(raw: str) -> str:
    slug = _SLUG_RE.sub("_", raw.lower()).strip("_")
    if not slug or not slug[0].isalpha():
        slug = f"a_{slug}" if slug else "achievement"
    return slug[:MAX_ACHIEVEMENT_SLUG]


def _unique_slug(db: Session, base: str) -> str:
    candidate = base
    index = 2
    while db.scalar(select(Achievement.id).where(Achievement.slug == candidate)) is not None:
        suffix = f"_{index}"
        candidate = f"{base[: MAX_ACHIEVEMENT_SLUG - len(suffix)]}{suffix}"
        index += 1
    return candidate


def _staff_query() -> Select[Achievement]:
    return select(Achievement).options(
        selectinload(Achievement.rewards).selectinload(AchievementReward.pack),
        selectinload(Achievement.rewards)
        .selectinload(AchievementReward.catalog_icon)
        .selectinload(CatalogIcon.pack),
    )


def get_achievement_or_raise(db: Session, achievement_id: uuid.UUID) -> Achievement:
    achievement = db.scalar(_staff_query().where(Achievement.id == achievement_id))
    if achievement is None:
        raise AchievementError(
            "Achievement not found",
            code=ErrorCode.ACHIEVEMENT_NOT_FOUND,
            status_code=404,
        )
    return achievement


def list_staff_achievements(db: Session) -> list[Achievement]:
    return list(db.scalars(_staff_query().order_by(Achievement.sort_order, Achievement.slug)))


def unlocked_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(UserAchievement.achievement_id, func.count(UserAchievement.id))
        .where(UserAchievement.unlocked_at.is_not(None))
        .group_by(UserAchievement.achievement_id)
    ).all()
    return {achievement_id: int(count) for achievement_id, count in rows}


def _choice(value: str, allowed: frozenset[str], *, field: str) -> str:
    if value not in allowed:
        raise AchievementError(
            f"Invalid {field}",
            code=ErrorCode.INVALID_ACHIEVEMENT_FIELD,
            params={"field": field},
        )
    return value


def _criteria(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        return normalize_criteria(raw)
    except InvalidCriteriaError as exc:
        raise AchievementError(
            str(exc),
            code=ErrorCode.INVALID_ACHIEVEMENT_CRITERIA,
            params={"param": exc.param or ""},
        ) from exc


def _emoji(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned[:MAX_ACHIEVEMENT_EMOJI] or DEFAULT_ACHIEVEMENT_ICON


def _invalid_reward(message: str) -> AchievementError:
    return AchievementError(message, code=ErrorCode.INVALID_ACHIEVEMENT_REWARD)


def _replace_rewards(db: Session, achievement: Achievement, rewards: list[RewardInput]) -> None:
    built: list[AchievementReward] = []
    for index, reward in enumerate(rewards):
        item = AchievementReward(kind=reward.kind, sort_order=(index + 1) * 10)
        if reward.kind == AchievementRewardKind.TOKENS.value:
            if reward.amount is None or reward.amount <= 0:
                raise _invalid_reward("Token reward needs a positive amount")
            item.amount = reward.amount
        elif reward.kind == AchievementRewardKind.ICON_PACK.value:
            if reward.pack_id is None or db.get(IconPack, reward.pack_id) is None:
                raise _invalid_reward("Pack reward needs an existing pack")
            item.pack_id = reward.pack_id
        elif reward.kind == AchievementRewardKind.CATALOG_ICON.value:
            icon_id = reward.catalog_icon_id
            if icon_id is None or db.get(CatalogIcon, icon_id) is None:
                raise _invalid_reward("Icon reward needs an existing catalog icon")
            item.catalog_icon_id = reward.catalog_icon_id
        else:
            raise _invalid_reward("Unknown reward kind")
        built.append(item)
    achievement.rewards = built


def create_achievement(
    db: Session,
    *,
    labels: dict[str, str],
    descriptions: dict[str, str],
    category: str,
    visibility: str,
    criteria: dict[str, Any],
    rewards: list[RewardInput],
    emoji: str | None = None,
    slug: str | None = None,
    sort_order: int | None = None,
) -> Achievement:
    base = _slugify(slug or resolve_label(labels, "en"))
    if slug and db.scalar(select(Achievement.id).where(Achievement.slug == base)) is not None:
        raise AchievementError(
            "Achievement slug already exists",
            code=ErrorCode.ACHIEVEMENT_SLUG_TAKEN,
            status_code=409,
            params={"slug": base},
        )
    if sort_order is None:
        last = db.scalar(select(func.max(Achievement.sort_order)))
        sort_order = int(last or 0) + 10
    achievement = Achievement(
        slug=_unique_slug(db, base),
        labels=labels,
        descriptions=descriptions,
        category=_choice(category, ACHIEVEMENT_CATEGORIES, field="category"),
        visibility=_choice(visibility, ACHIEVEMENT_VISIBILITIES, field="visibility"),
        # New achievements start hidden so staff can check them before publishing.
        status=AchievementStatus.DRAFT.value,
        icon_type=AchievementIconType.EMOJI.value,
        icon=_emoji(emoji),
        criteria=_criteria(criteria),
        sort_order=sort_order,
    )
    db.add(achievement)
    db.flush()
    _replace_rewards(db, achievement, rewards)
    db.flush()
    return achievement


def update_achievement(
    db: Session,
    *,
    achievement_id: uuid.UUID,
    labels: dict[str, str] | None = None,
    descriptions: dict[str, str] | None = None,
    category: str | None = None,
    visibility: str | None = None,
    status: str | None = None,
    criteria: dict[str, Any] | None = None,
    rewards: list[RewardInput] | None = None,
    emoji: str | None = None,
    sort_order: int | None = None,
) -> Achievement:
    """Edit an achievement. Users who already unlocked it keep it and its rewards."""
    achievement = get_achievement_or_raise(db, achievement_id)
    if labels is not None:
        achievement.labels = labels
    if descriptions is not None:
        achievement.descriptions = descriptions
    if category is not None:
        achievement.category = _choice(category, ACHIEVEMENT_CATEGORIES, field="category")
    if visibility is not None:
        achievement.visibility = _choice(visibility, ACHIEVEMENT_VISIBILITIES, field="visibility")
    if status is not None:
        achievement.status = _choice(status, ACHIEVEMENT_STATUSES, field="status")
    if criteria is not None:
        achievement.criteria = _criteria(criteria)
    if emoji is not None:
        achievement.icon = _emoji(emoji)
        if achievement.icon_type == AchievementIconType.IMAGE.value:
            # Choosing an emoji switches the icon back from an image.
            achievement.icon_type = AchievementIconType.EMOJI.value
    if sort_order is not None:
        achievement.sort_order = sort_order
    if rewards is not None:
        _replace_rewards(db, achievement, rewards)
    db.flush()
    return achievement


def set_achievement_icon_image(
    db: Session,
    *,
    achievement_id: uuid.UUID,
    storage: ObjectStorage,
    data: bytes,
    content_type: str,
) -> Achievement:
    achievement = get_achievement_or_raise(db, achievement_id)
    mime_type = content_type.split(";")[0].strip().lower()
    if mime_type not in ALLOWED_CATALOG_MIME_TYPES:
        raise AchievementError(
            "Unsupported image MIME type",
            code=ErrorCode.UNSUPPORTED_IMAGE_MIME,
            params={"mime": mime_type},
        )
    if len(data) > MAX_CATALOG_ICON_BYTES:
        raise AchievementError(
            "Icon exceeds 512 KB limit",
            code=ErrorCode.ICON_TOO_LARGE,
            params={"limit": "512KB"},
        )
    old_key = achievement.icon_storage_key
    key = f"achievements/{achievement.id}/{uuid.uuid4()}"
    storage.put_object(key=key, data=data, content_type=mime_type)
    achievement.icon_type = AchievementIconType.IMAGE.value
    achievement.icon_storage_key = key
    achievement.icon_mime_type = mime_type
    db.flush()
    if old_key:
        with contextlib.suppress(StorageError):
            storage.delete_object(key=old_key)
    return achievement


def can_view_achievement_icon(db: Session, *, user: User, achievement: Achievement) -> bool:
    if user.is_staff:
        return True
    if achievement.status != AchievementStatus.PUBLISHED.value:
        return False
    if achievement.visibility != AchievementVisibility.SECRET.value:
        return True
    unlocked_at = db.scalar(
        select(UserAchievement.unlocked_at).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == achievement.id,
        )
    )
    return unlocked_at is not None


def download_achievement_icon(
    db: Session,
    *,
    user: User,
    achievement_id: uuid.UUID,
    storage: ObjectStorage,
) -> tuple[Achievement, bytes]:
    achievement = db.get(Achievement, achievement_id)
    if (
        achievement is None
        or achievement.icon_type != AchievementIconType.IMAGE.value
        or not achievement.icon_storage_key
        or not can_view_achievement_icon(db, user=user, achievement=achievement)
    ):
        raise AchievementError(
            "Achievement icon not found",
            code=ErrorCode.ACHIEVEMENT_ICON_NOT_FOUND,
            status_code=404,
        )
    return achievement, storage.get_object(key=achievement.icon_storage_key)


def serialize_reward_input(reward: AchievementReward, *, locale: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "kind": reward.kind,
        "amount": reward.amount,
        "pack_id": reward.pack_id,
        "catalog_icon_id": reward.catalog_icon_id,
        "icon_pack_id": reward.catalog_icon.pack_id if reward.catalog_icon is not None else None,
        "label": None,
    }
    if reward.pack is not None:
        item["label"] = resolve_label((reward.pack.labels or {}).get("name") or {}, locale)
    elif reward.catalog_icon is not None:
        item["label"] = resolve_label(reward.catalog_icon.labels, locale)
    return item


def serialize_staff_achievement(
    achievement: Achievement,
    *,
    locale: str,
    unlocked_count: int = 0,
) -> dict[str, Any]:
    return {
        "id": achievement.id,
        "slug": achievement.slug,
        "category": achievement.category,
        "visibility": achievement.visibility,
        "status": achievement.status,
        "labels": achievement.labels,
        "descriptions": achievement.descriptions,
        "name": resolve_label(achievement.labels, locale),
        "icon_type": achievement.icon_type,
        "icon": achievement.icon,
        "criteria": achievement.criteria,
        "sort_order": achievement.sort_order,
        "rewards": [
            serialize_reward_input(reward, locale=locale)
            for reward in sorted(achievement.rewards, key=lambda item: item.sort_order)
        ],
        "unlocked_count": unlocked_count,
        "updated_at": achievement.updated_at,
    }
