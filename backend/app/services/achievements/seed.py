"""Seed published achievements from catalog.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.achievements import (
    ACHIEVEMENT_CATEGORIES,
    ACHIEVEMENT_REWARD_KINDS,
    ACHIEVEMENT_STATUSES,
    ACHIEVEMENT_VISIBILITIES,
    CRITERIA_TYPES,
    DEFAULT_ACHIEVEMENT_ICON,
    DEFAULT_ACHIEVEMENT_ICON_TYPE,
    AchievementRewardKind,
    AchievementStatus,
)
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "achievements" / "catalog.json"


def _load_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    catalog_path = path or _CATALOG_PATH
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Achievement catalog must be a JSON array")
    return raw


def _require_labels(value: Any, *, field: str, slug: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"Achievement {slug}: {field} must be a non-empty locale map")
    return {str(k): str(v) for k, v in value.items()}


def _resolve_pack(db: Session, pack_slug: str) -> IconPack:
    pack = db.scalar(select(IconPack).where(IconPack.slug == pack_slug))
    if pack is None:
        raise ValueError(f"Icon pack not found: {pack_slug}")
    return pack


def _resolve_catalog_icon(db: Session, *, pack_slug: str, icon_slug: str) -> CatalogIcon:
    pack = _resolve_pack(db, pack_slug)
    icon = db.scalar(
        select(CatalogIcon).where(
            CatalogIcon.pack_id == pack.id,
            CatalogIcon.slug == icon_slug,
        )
    )
    if icon is None:
        raise ValueError(f"Catalog icon not found: {pack_slug}/{icon_slug}")
    return icon


def _parse_rewards(
    db: Session,
    *,
    slug: str,
    raw_rewards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rewards):
        kind = raw.get("kind")
        if kind not in ACHIEVEMENT_REWARD_KINDS:
            raise ValueError(f"Achievement {slug}: unknown reward kind {kind!r}")
        item: dict[str, Any] = {
            "kind": kind,
            "sort_order": int(raw.get("sort_order", (index + 1) * 10)),
            "amount": None,
            "pack_id": None,
            "catalog_icon_id": None,
        }
        if kind == AchievementRewardKind.TOKENS.value:
            amount = int(raw.get("amount", 0))
            if amount <= 0:
                raise ValueError(f"Achievement {slug}: tokens amount must be > 0")
            item["amount"] = amount
        elif kind == AchievementRewardKind.ICON_PACK.value:
            pack_slug = raw.get("pack_slug")
            if not pack_slug:
                raise ValueError(f"Achievement {slug}: icon_pack requires pack_slug")
            item["pack_id"] = _resolve_pack(db, str(pack_slug)).id
        elif kind == AchievementRewardKind.CATALOG_ICON.value:
            pack_slug = raw.get("pack_slug")
            icon_slug = raw.get("icon_slug")
            if not pack_slug or not icon_slug:
                raise ValueError(
                    f"Achievement {slug}: catalog_icon requires pack_slug and icon_slug"
                )
            item["catalog_icon_id"] = _resolve_catalog_icon(
                db,
                pack_slug=str(pack_slug),
                icon_slug=str(icon_slug),
            ).id
        parsed.append(item)
    return parsed


def _upsert_one(db: Session, raw: dict[str, Any]) -> Achievement:
    slug = str(raw["slug"]).strip()
    if not slug:
        raise ValueError("Achievement slug is required")

    category = raw.get("category")
    visibility = raw.get("visibility")
    status = raw.get("status", AchievementStatus.PUBLISHED.value)
    if category not in ACHIEVEMENT_CATEGORIES:
        raise ValueError(f"Achievement {slug}: invalid category {category!r}")
    if visibility not in ACHIEVEMENT_VISIBILITIES:
        raise ValueError(f"Achievement {slug}: invalid visibility {visibility!r}")
    if status not in ACHIEVEMENT_STATUSES:
        raise ValueError(f"Achievement {slug}: invalid status {status!r}")

    criteria = raw.get("criteria") or {}
    if criteria.get("type") not in CRITERIA_TYPES:
        raise ValueError(f"Achievement {slug}: invalid criteria type")

    icon_meta = raw.get("icon") or {}
    icon_type = str(icon_meta.get("type") or DEFAULT_ACHIEVEMENT_ICON_TYPE)
    icon = str(icon_meta.get("value") or DEFAULT_ACHIEVEMENT_ICON)

    rewards = _parse_rewards(db, slug=slug, raw_rewards=list(raw.get("rewards") or []))

    achievement = db.scalar(
        select(Achievement)
        .where(Achievement.slug == slug)
        .options(selectinload(Achievement.rewards))
    )
    if achievement is None:
        achievement = Achievement(slug=slug)
        db.add(achievement)

    achievement.category = category
    achievement.visibility = visibility
    achievement.status = status
    achievement.labels = _require_labels(raw.get("labels"), field="labels", slug=slug)
    achievement.descriptions = _require_labels(
        raw.get("descriptions"),
        field="descriptions",
        slug=slug,
    )
    achievement.icon_type = icon_type
    achievement.icon = icon
    achievement.criteria = criteria
    achievement.sort_order = int(raw.get("sort_order", 0))
    db.flush()

    db.execute(
        delete(AchievementReward).where(AchievementReward.achievement_id == achievement.id)
    )
    for reward in rewards:
        db.add(
            AchievementReward(
                achievement_id=achievement.id,
                kind=reward["kind"],
                amount=reward["amount"],
                pack_id=reward["pack_id"],
                catalog_icon_id=reward["catalog_icon_id"],
                sort_order=reward["sort_order"],
            )
        )
    db.flush()
    return achievement


def seed_achievements(db: Session, *, path: Path | None = None) -> list[Achievement]:
    """Idempotent upsert of catalog achievements. Pack/icon rewards must already exist."""
    items = _load_catalog(path)
    return [_upsert_one(db, raw) for raw in items]


def main() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        achievements = seed_achievements(db)
        db.commit()
        for achievement in achievements:
            print(
                f"Seeded achievement slug={achievement.slug} "
                f"id={achievement.id} rewards={len(achievement.rewards)}"
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
