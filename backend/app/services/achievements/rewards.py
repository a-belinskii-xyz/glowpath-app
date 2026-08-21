"""Grant achievement rewards (tokens, packs, single catalog icons)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.achievements import AchievementRewardKind
from app.core.i18n import resolve_label
from app.core.marketplace import WalletLedgerKind
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.icon_pack_unlock import IconPackUnlock
from app.models.user_catalog_icon_unlock import UserCatalogIconUnlock
from app.services.wallet_service import apply_ledger_delta, get_or_create_wallet

PACK_PREVIEW_ICON_LIMIT = 3


def _pack_preview_icon_ids(db: Session, *, pack: IconPack) -> list[str]:
    """Up to 3 icon ids for stacked pack preview; cover first when set."""
    ids: list[uuid.UUID] = []
    if pack.cover_icon_id is not None:
        ids.append(pack.cover_icon_id)
    remaining = PACK_PREVIEW_ICON_LIMIT - len(ids)
    if remaining <= 0:
        return [str(icon_id) for icon_id in ids[:PACK_PREVIEW_ICON_LIMIT]]

    query = select(CatalogIcon.id).where(CatalogIcon.pack_id == pack.id)
    if ids:
        query = query.where(CatalogIcon.id.notin_(ids))
    extras = list(
        db.scalars(
            query.order_by(CatalogIcon.sort_order, CatalogIcon.created_at).limit(remaining)
        ).all()
    )
    ids.extend(extras)
    return [str(icon_id) for icon_id in ids[:PACK_PREVIEW_ICON_LIMIT]]


def _reward_snapshot_item(
    db: Session,
    reward: AchievementReward,
    *,
    locale: str,
) -> dict[str, Any]:
    item: dict[str, Any] = {"kind": reward.kind}
    if reward.kind == AchievementRewardKind.TOKENS.value:
        item["amount"] = reward.amount
    elif reward.kind == AchievementRewardKind.ICON_PACK.value and reward.pack is not None:
        pack: IconPack = reward.pack
        item["pack_id"] = str(reward.pack_id)
        item["pack_slug"] = pack.slug
        item["pack_name"] = resolve_label(
            (pack.labels or {}).get("name") or {},
            locale,
        ) or pack.slug
        item["cover_icon_id"] = str(pack.cover_icon_id) if pack.cover_icon_id else None
        item["preview_icon_ids"] = _pack_preview_icon_ids(db, pack=pack)
    elif (
        reward.kind == AchievementRewardKind.CATALOG_ICON.value
        and reward.catalog_icon is not None
    ):
        item["catalog_icon_id"] = str(reward.catalog_icon_id)
        item["icon_slug"] = reward.catalog_icon.slug
        item["icon_name"] = resolve_label(reward.catalog_icon.labels, locale)
        if reward.catalog_icon.pack is not None:
            item["pack_id"] = str(reward.catalog_icon.pack_id)
            item["pack_slug"] = reward.catalog_icon.pack.slug
    return item


def grant_rewards(
    db: Session,
    *,
    user_id: uuid.UUID,
    achievement: Achievement,
    locale: str = "en",
) -> list[dict[str, Any]]:
    """Apply rewards. Packs/icons are idempotent; tokens once via unlock gate."""
    rewards = list(
        db.scalars(
            select(AchievementReward)
            .where(AchievementReward.achievement_id == achievement.id)
            .options(
                selectinload(AchievementReward.pack),
                selectinload(AchievementReward.catalog_icon).selectinload(CatalogIcon.pack),
            )
            .order_by(AchievementReward.sort_order)
        ).all()
    )
    snapshot: list[dict[str, Any]] = []
    for reward in rewards:
        if reward.kind == AchievementRewardKind.TOKENS.value and reward.amount:
            apply_ledger_delta(
                db,
                user_id=user_id,
                delta=reward.amount,
                kind=WalletLedgerKind.ACHIEVEMENT,
                achievement_id=achievement.id,
                note=f"Achievement {achievement.slug}",
            )
        elif reward.kind == AchievementRewardKind.ICON_PACK.value and reward.pack_id is not None:
            get_or_create_wallet(db, user_id=user_id)
            existing = db.scalar(
                select(IconPackUnlock).where(
                    IconPackUnlock.user_id == user_id,
                    IconPackUnlock.pack_id == reward.pack_id,
                )
            )
            if existing is None:
                db.add(IconPackUnlock(user_id=user_id, pack_id=reward.pack_id))
                db.flush()
        elif (
            reward.kind == AchievementRewardKind.CATALOG_ICON.value
            and reward.catalog_icon_id is not None
        ):
            existing_icon = db.scalar(
                select(UserCatalogIconUnlock).where(
                    UserCatalogIconUnlock.user_id == user_id,
                    UserCatalogIconUnlock.catalog_icon_id == reward.catalog_icon_id,
                )
            )
            if existing_icon is None:
                db.add(
                    UserCatalogIconUnlock(
                        user_id=user_id,
                        catalog_icon_id=reward.catalog_icon_id,
                    )
                )
                db.flush()
        snapshot.append(_reward_snapshot_item(db, reward, locale=locale))
    return snapshot


def serialize_reward_public(
    db: Session,
    reward: AchievementReward,
    *,
    locale: str,
) -> dict[str, Any]:
    return _reward_snapshot_item(db, reward, locale=locale)
