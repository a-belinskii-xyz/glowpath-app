"""Achievement evaluation, listing, and unlock orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.achievements import (
    AchievementStatus,
    AchievementVisibility,
)
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_user
from app.core.i18n import resolve_label
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.services.achievements.criteria import (
    evaluate_criteria,
    progress_target_for_criteria,
)
from app.services.achievements.rewards import grant_rewards, serialize_reward_public


class AchievementError(AppError):
    pass


def _published_achievements_query():
    return (
        select(Achievement)
        .where(Achievement.status == AchievementStatus.PUBLISHED.value)
        .options(
            selectinload(Achievement.rewards)
            .selectinload(AchievementReward.pack),
            selectinload(Achievement.rewards)
            .selectinload(AchievementReward.catalog_icon)
            .selectinload(CatalogIcon.pack),
        )
        .order_by(Achievement.sort_order, Achievement.slug)
    )


def _user_progress_map(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> dict[uuid.UUID, UserAchievement]:
    rows = db.scalars(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    ).all()
    return {row.achievement_id: row for row in rows}


def _get_or_create_progress(
    db: Session,
    *,
    user_id: uuid.UUID,
    achievement: Achievement,
    progress_map: dict[uuid.UUID, UserAchievement],
) -> UserAchievement:
    existing = progress_map.get(achievement.id)
    if existing is not None:
        return existing
    row = UserAchievement(
        user_id=user_id,
        achievement_id=achievement.id,
        progress_current=0,
        progress_target=progress_target_for_criteria(achievement.criteria),
    )
    db.add(row)
    db.flush()
    progress_map[achievement.id] = row
    return row


def _eligible_user_count(db: Session) -> int:
    """Denominator for rarity: verified users."""
    return int(
        db.scalar(
            select(func.count()).select_from(User).where(User.email_verified_at.is_not(None))
        )
        or 0
    )


def unlock_rates_by_achievement(
    db: Session,
    *,
    achievement_ids: list[uuid.UUID] | None = None,
) -> dict[uuid.UUID, float]:
    """Return unlock percent (0–100) per achievement among verified users."""
    eligible = _eligible_user_count(db)
    if eligible <= 0:
        return {}

    stmt = (
        select(
            UserAchievement.achievement_id,
            func.count(UserAchievement.id),
        )
        .where(UserAchievement.unlocked_at.is_not(None))
        .group_by(UserAchievement.achievement_id)
    )
    if achievement_ids is not None:
        if not achievement_ids:
            return {}
        stmt = stmt.where(UserAchievement.achievement_id.in_(achievement_ids))

    rates: dict[uuid.UUID, float] = {}
    for achievement_id, unlocked_count in db.execute(stmt).all():
        rates[achievement_id] = round(100.0 * int(unlocked_count) / eligible, 1)
    return rates


def evaluate_user_achievements(
    db: Session,
    *,
    user: User,
    locale: str = "en",
    source_entry_id: uuid.UUID | None = None,
) -> list[Achievement]:
    """Recompute progress and unlock newly completed achievements.

    Returns achievements unlocked during this call (for toast payloads).
    Does nothing when the feature flag is off.
    """
    if not is_feature_enabled_for_user(FeatureFlag.ACHIEVEMENTS, user):
        return []

    achievements = list(db.scalars(_published_achievements_query()).all())
    progress_map = _user_progress_map(db, user_id=user.id)
    newly_unlocked: list[Achievement] = []

    for achievement in achievements:
        progress = progress_map.get(achievement.id)
        already_unlocked = progress is not None and progress.unlocked_at is not None
        result = evaluate_criteria(db, user=user, criteria=achievement.criteria)

        if already_unlocked:
            # Sticky unlock: keep unlocked_at; optionally refresh target display.
            progress.progress_target = result.target
            progress.progress_current = max(progress.progress_current, result.target)
            continue

        if result.current == 0 and progress is None:
            continue

        progress = _get_or_create_progress(
            db,
            user_id=user.id,
            achievement=achievement,
            progress_map=progress_map,
        )
        progress.progress_target = result.target
        progress.progress_current = result.current

        if result.complete:
            progress.unlocked_at = datetime.now(UTC)
            if source_entry_id is not None:
                progress.unlocked_by_entry_id = source_entry_id
            snapshot = grant_rewards(
                db,
                user_id=user.id,
                achievement=achievement,
                locale=locale,
            )
            progress.rewards_snapshot = snapshot
            newly_unlocked.append(achievement)

    db.flush()
    return newly_unlocked


def mark_achievement_seen(
    db: Session,
    *,
    user: User,
    achievement_id: uuid.UUID,
) -> UserAchievement:
    progress = db.scalar(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == achievement_id,
        )
    )
    if progress is None or progress.unlocked_at is None:
        raise AchievementError(
            "Achievement not unlocked",
            code=ErrorCode.ACHIEVEMENT_NOT_UNLOCKED,
            status_code=404,
        )
    progress.seen_at = datetime.now(UTC)
    db.flush()
    return progress


def serialize_achievement_public(
    db: Session,
    achievement: Achievement,
    *,
    progress: UserAchievement | None,
    locale: str,
    unlock_percent: float | None = None,
) -> dict[str, Any]:
    unlocked = progress is not None and progress.unlocked_at is not None
    is_secret = achievement.visibility == AchievementVisibility.SECRET.value

    if is_secret and not unlocked:
        payload = {
            "id": achievement.id,
            "visibility": achievement.visibility,
            "category": achievement.category,
            "unlocked": False,
            "is_new": False,
            "progress_current": 0,
            "progress_target": 1,
            "sort_order": achievement.sort_order,
        }
        if unlock_percent is not None:
            payload["unlock_percent"] = unlock_percent
        return payload

    rewards = [
        serialize_reward_public(db, reward, locale=locale)
        for reward in sorted(achievement.rewards, key=lambda r: r.sort_order)
    ]
    if unlocked and progress is not None and progress.rewards_snapshot:
        # Prefer live cover/preview ids when snapshot is older.
        live_by_kind = {
            (r.get("kind"), r.get("pack_id") or r.get("catalog_icon_id")): r for r in rewards
        }
        merged: list[dict[str, Any]] = []
        for snap in progress.rewards_snapshot:
            if not isinstance(snap, dict):
                continue
            key = (snap.get("kind"), snap.get("pack_id") or snap.get("catalog_icon_id"))
            live = live_by_kind.get(key)
            if live is not None:
                merged.append({**snap, **{k: v for k, v in live.items() if v is not None}})
            else:
                merged.append(dict(snap))
        rewards = merged

    return {
        "id": achievement.id,
        "slug": achievement.slug,
        "visibility": achievement.visibility,
        "category": achievement.category,
        "name": resolve_label(achievement.labels, locale),
        "description": resolve_label(achievement.descriptions, locale),
        "icon_type": achievement.icon_type,
        "icon": achievement.icon,
        "criteria": achievement.criteria,
        "rewards": rewards,
        "unlocked": unlocked,
        "unlocked_at": progress.unlocked_at if progress else None,
        "unlocked_by_entry_id": (
            progress.unlocked_by_entry_id
            if progress is not None and unlocked
            else None
        ),
        "unlock_percent": unlock_percent,
        "is_new": bool(
            unlocked
            and progress is not None
            and progress.seen_at is None
        ),
        "progress_current": (
            progress.progress_current
            if progress is not None
            else 0
        ),
        "progress_target": (
            progress.progress_target
            if progress is not None
            else progress_target_for_criteria(achievement.criteria)
        ),
        "sort_order": achievement.sort_order,
    }


def list_achievements_for_user(
    db: Session,
    *,
    user: User,
    locale: str,
) -> list[dict[str, Any]]:
    evaluate_user_achievements(db, user=user, locale=locale)
    achievements = list(db.scalars(_published_achievements_query()).all())
    progress_map = _user_progress_map(db, user_id=user.id)
    rates = unlock_rates_by_achievement(
        db,
        achievement_ids=[achievement.id for achievement in achievements],
    )
    return [
        serialize_achievement_public(
            db,
            achievement,
            progress=progress_map.get(achievement.id),
            locale=locale,
            unlock_percent=rates.get(achievement.id, 0.0),
        )
        for achievement in achievements
    ]


def achievements_summary(
    db: Session,
    *,
    user: User,
    locale: str = "en",
) -> dict[str, int]:
    evaluate_user_achievements(db, user=user, locale=locale)
    achievements = list(db.scalars(_published_achievements_query()).all())
    progress_map = _user_progress_map(db, user_id=user.id)

    unlocked_visible = 0
    total_visible = 0
    secret_unlocked = 0
    secret_total = 0

    for achievement in achievements:
        progress = progress_map.get(achievement.id)
        is_unlocked = progress is not None and progress.unlocked_at is not None
        if achievement.visibility == AchievementVisibility.SECRET.value:
            secret_total += 1
            if is_unlocked:
                secret_unlocked += 1
        else:
            total_visible += 1
            if is_unlocked:
                unlocked_visible += 1

    return {
        "unlocked": unlocked_visible,
        "total_visible": total_visible,
        "secret_unlocked": secret_unlocked,
        "secret_total": secret_total,
    }


def serialize_unlocked_list(
    db: Session,
    *,
    user: User,
    unlocked: list[Achievement],
    locale: str,
) -> list[dict[str, Any]]:
    if not unlocked:
        return []
    progress_map = _user_progress_map(db, user_id=user.id)
    rates = unlock_rates_by_achievement(
        db,
        achievement_ids=[achievement.id for achievement in unlocked],
    )
    return [
        serialize_achievement_public(
            db,
            achievement,
            progress=progress_map.get(achievement.id),
            locale=locale,
            unlock_percent=rates.get(achievement.id, 0.0),
        )
        for achievement in unlocked
    ]
