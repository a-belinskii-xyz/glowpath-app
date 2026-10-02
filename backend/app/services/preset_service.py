"""Catalog presets: export packs + achievements as seed folders, import them elsewhere.

A preset uses the same on-disk format as the repo seeds, so an unpacked archive can
also be dropped into ``backend/app/data/`` and loaded with ``make seed-marketplace``
and ``make seed-achievements``::

    manifest.json
    marketplace/search-tags.json
    marketplace/<pack-slug>/pack.json
    marketplace/<pack-slug>/<icon-slug>.<ext>
    achievements/catalog.json
"""

from __future__ import annotations

import io
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.achievements import AchievementIconType, AchievementRewardKind
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.marketplace import ESSENTIALS_PACK_SLUG, PackStatus
from app.models.achievement import Achievement
from app.models.icon_pack import IconPack
from app.models.icon_search_tag import IconSearchTag
from app.services.achievements.seed import seed_achievements
from app.services.marketplace_seed import (
    seed_default_search_tags,
    seed_essentials_pack,
    seed_mock_packs,
)
from app.services.storage import ObjectStorage

PRESET_FORMAT = "glowpath-preset"
PRESET_VERSION = 1
MANIFEST_FILENAME = "manifest.json"
SEARCH_TAGS_FILENAME = "search-tags.json"
ACHIEVEMENTS_FILENAME = "catalog.json"

MAX_PRESET_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_PRESET_UNPACKED_BYTES = 256 * 1024 * 1024
MAX_PRESET_FILES = 5000

_EXTENSION_BY_MIME: dict[str, str] = {
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

# Seed folders only know draft / published / archived.
_EXPORT_STATUS: dict[str, str] = {
    PackStatus.PUBLISHED.value: PackStatus.PUBLISHED.value,
    PackStatus.ARCHIVED.value: PackStatus.ARCHIVED.value,
}


class PresetError(AppError):
    pass


@dataclass(slots=True)
class PresetImportReport:
    search_tags: int = 0
    packs: list[str] = field(default_factory=list)
    icons: int = 0
    achievements: list[str] = field(default_factory=list)


# --- Export ---


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _pack_json(pack: IconPack) -> dict[str, Any]:
    labels = pack.labels or {}
    cover_slug = next(
        (icon.slug for icon in pack.icons if icon.id == pack.cover_icon_id),
        None,
    )
    payload: dict[str, Any] = {
        "slug": pack.slug,
        "name": labels.get("name") or {"en": pack.slug},
        "description": labels.get("description") or labels.get("name") or {"en": pack.slug},
        "price_tokens": pack.price_tokens,
        "official": pack.is_official,
        "status": _EXPORT_STATUS.get(pack.status, PackStatus.DRAFT.value),
        "granted": pack.price_tokens == 0,
        "sort_order": pack.sort_order,
    }
    if cover_slug:
        payload["cover"] = cover_slug
    payload["icons"] = {
        icon.slug: {
            "file": f"{icon.slug}{_EXTENSION_BY_MIME.get(icon.mime_type, '.bin')}",
            "labels": icon.labels,
            "tags": [tag.slug for tag in icon.search_tags],
            "colors": list(icon.suggested_colors or []),
            "scores": list(icon.suggested_mood_scores or []),
            "usage": list(icon.suggested_usage or []),
            **({"crop": icon.crop} if icon.crop else {}),
            "sort_order": icon.sort_order,
        }
        for icon in pack.icons
    }
    return payload


def _achievement_json(achievement: Achievement) -> dict[str, Any]:
    rewards: list[dict[str, Any]] = []
    for reward in achievement.rewards:
        if reward.kind == AchievementRewardKind.TOKENS.value and reward.amount:
            rewards.append({"kind": reward.kind, "amount": reward.amount})
        elif reward.kind == AchievementRewardKind.ICON_PACK.value and reward.pack is not None:
            rewards.append({"kind": reward.kind, "pack_slug": reward.pack.slug})
        elif (
            reward.kind == AchievementRewardKind.CATALOG_ICON.value
            and reward.catalog_icon is not None
        ):
            rewards.append(
                {
                    "kind": reward.kind,
                    "pack_slug": reward.catalog_icon.pack.slug,
                    "icon_slug": reward.catalog_icon.slug,
                }
            )
        else:
            # Reward target was deleted (FK SET NULL); nothing portable to export.
            continue
        rewards[-1]["sort_order"] = reward.sort_order
    return {
        "slug": achievement.slug,
        "category": achievement.category,
        "visibility": achievement.visibility,
        "status": achievement.status,
        "sort_order": achievement.sort_order,
        "labels": achievement.labels,
        "descriptions": achievement.descriptions,
        "icon": _achievement_icon_json(achievement),
        "criteria": achievement.criteria,
        "rewards": rewards,
    }


def _achievement_icon_file(achievement: Achievement) -> str | None:
    if achievement.icon_type != AchievementIconType.IMAGE.value or not achievement.icon_mime_type:
        return None
    extension = _EXTENSION_BY_MIME.get(achievement.icon_mime_type, "")
    return f"icons/{achievement.slug}{extension}"


def _achievement_icon_json(achievement: Achievement) -> dict[str, Any]:
    icon: dict[str, Any] = {"type": achievement.icon_type, "value": achievement.icon}
    file_name = _achievement_icon_file(achievement)
    if file_name is not None:
        icon["file"] = file_name
    return icon


def _reward_pack_ids(achievements: list[Achievement]) -> set[Any]:
    ids: set[Any] = set()
    for achievement in achievements:
        for reward in achievement.rewards:
            if reward.pack_id is not None:
                ids.add(reward.pack_id)
            if reward.catalog_icon is not None:
                ids.add(reward.catalog_icon.pack_id)
    return ids


def export_preset(
    db: Session,
    *,
    storage: ObjectStorage,
    pack_ids: list[Any] | None = None,
    include_achievements: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    """Build a preset zip. ``pack_ids=None`` exports every official pack.

    Packs referenced by exported achievement rewards are always included so the
    preset imports cleanly on an empty instance. ``essentials`` is never exported:
    every instance seeds it from the builtin icons.
    """
    achievements: list[Achievement] = []
    if include_achievements:
        achievements = list(
            db.scalars(
                select(Achievement)
                .options(selectinload(Achievement.rewards))
                .order_by(Achievement.sort_order, Achievement.slug)
            ).all()
        )

    pack_query = select(IconPack).options(selectinload(IconPack.icons))
    if pack_ids is None:
        pack_query = pack_query.where(IconPack.is_official.is_(True))
    else:
        wanted = set(pack_ids) | _reward_pack_ids(achievements)
        pack_query = pack_query.where(IconPack.id.in_(wanted))
    packs = [
        pack
        for pack in db.scalars(pack_query.order_by(IconPack.sort_order, IconPack.slug)).all()
        if pack.slug != ESSENTIALS_PACK_SLUG
    ]
    if pack_ids is None and achievements:
        exported = {pack.id for pack in packs}
        missing = _reward_pack_ids(achievements) - exported
        if missing:
            packs.extend(
                pack
                for pack in db.scalars(
                    select(IconPack)
                    .options(selectinload(IconPack.icons))
                    .where(IconPack.id.in_(missing))
                ).all()
                if pack.slug != ESSENTIALS_PACK_SLUG
            )

    used_tag_slugs = {tag.slug for pack in packs for icon in pack.icons for tag in icon.search_tags}
    search_tags = [
        {
            "slug": tag.slug,
            "labels": tag.labels,
            "sort_order": tag.sort_order,
            "is_active": tag.is_active,
        }
        for tag in db.scalars(
            select(IconSearchTag).order_by(IconSearchTag.sort_order, IconSearchTag.slug)
        ).all()
        if tag.slug in used_tag_slugs
    ]

    manifest = {
        "format": PRESET_FORMAT,
        "version": PRESET_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "packs": [pack.slug for pack in packs],
        "icons": sum(len(pack.icons) for pack in packs),
        "achievements": [achievement.slug for achievement in achievements],
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_FILENAME, _json_bytes(manifest))
        archive.writestr(f"marketplace/{SEARCH_TAGS_FILENAME}", _json_bytes(search_tags))
        for pack in packs:
            meta = _pack_json(pack)
            archive.writestr(f"marketplace/{pack.slug}/pack.json", _json_bytes(meta))
            for icon in pack.icons:
                data = storage.get_object(key=icon.storage_key)
                file_name = meta["icons"][icon.slug]["file"]
                archive.writestr(f"marketplace/{pack.slug}/{file_name}", data)
        if include_achievements:
            catalog = [_achievement_json(achievement) for achievement in achievements]
            archive.writestr(f"achievements/{ACHIEVEMENTS_FILENAME}", _json_bytes(catalog))
            for achievement in achievements:
                file_name = _achievement_icon_file(achievement)
                if file_name is not None and achievement.icon_storage_key:
                    data = storage.get_object(key=achievement.icon_storage_key)
                    archive.writestr(f"achievements/{file_name}", data)
    return buffer.getvalue(), manifest


# --- Import ---


def _upsert_search_tags(db: Session, path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PresetError(
            f"Invalid JSON in {path.name}: {exc}",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        ) from exc
    if not isinstance(raw, list):
        raise PresetError(
            f"{path.name} must be a JSON array",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        )
    existing = {tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()}
    count = 0
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("slug"), str):
            continue
        slug = item["slug"].strip().lower()[:64]
        raw_labels = item.get("labels")
        raw_sort = item.get("sort_order")
        raw_active = item.get("is_active")
        labels: dict[str, Any] = raw_labels if isinstance(raw_labels, dict) else {"en": slug}
        sort_order = raw_sort if isinstance(raw_sort, int) else 0
        is_active = raw_active if isinstance(raw_active, bool) else True
        tag = existing.get(slug)
        if tag is None:
            tag = IconSearchTag(slug=slug)
            db.add(tag)
            existing[slug] = tag
        tag.labels = labels
        tag.sort_order = sort_order
        tag.is_active = is_active
        count += 1
    db.flush()
    return count


def import_preset_dir(db: Session, *, storage: ObjectStorage, root: Path) -> PresetImportReport:
    """Idempotent upsert of a preset folder (packs by slug, achievements by slug)."""
    marketplace_dir = root / "marketplace"
    catalog_path = root / "achievements" / ACHIEVEMENTS_FILENAME
    if not marketplace_dir.is_dir() and not catalog_path.is_file():
        raise PresetError(
            "Preset has neither marketplace/ nor achievements/catalog.json",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        )

    report = PresetImportReport()
    seed_default_search_tags(db)
    report.search_tags = _upsert_search_tags(db, marketplace_dir / SEARCH_TAGS_FILENAME)
    # Achievements may reward essentials icons; seeding it is idempotent.
    seed_essentials_pack(db, storage=storage)
    if marketplace_dir.is_dir():
        packs = seed_mock_packs(db, storage=storage, root=marketplace_dir)
        report.packs = [pack.slug for pack in packs]
        report.icons = sum(len(pack.icons) for pack in packs)
    if catalog_path.is_file():
        try:
            achievements = seed_achievements(db, path=catalog_path, storage=storage)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise PresetError(
                f"Achievements import failed: {exc}",
                code=ErrorCode.PRESET_IMPORT_FAILED,
            ) from exc
        report.achievements = [achievement.slug for achievement in achievements]
    return report


def _preset_root(extracted: Path) -> Path:
    """Accept archives with files at the root or wrapped in one top-level folder."""
    if (extracted / "marketplace").is_dir() or (extracted / "achievements").is_dir():
        return extracted
    children = [child for child in extracted.iterdir() if not child.name.startswith(".")]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted


def _safe_extract(archive: zipfile.ZipFile, target: Path) -> None:
    members = archive.infolist()
    if len(members) > MAX_PRESET_FILES:
        raise PresetError(
            "Preset archive has too many files",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        )
    if sum(member.file_size for member in members) > MAX_PRESET_UNPACKED_BYTES:
        raise PresetError(
            "Preset archive is too large when unpacked",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        )
    for member in members:
        name = PurePosixPath(member.filename)
        if name.is_absolute() or ".." in name.parts:
            raise PresetError(
                f"Unsafe path in preset archive: {member.filename}",
                code=ErrorCode.PRESET_INVALID_ARCHIVE,
            )
        if "__MACOSX" in name.parts:
            continue
        destination = target.joinpath(*name.parts)
        if member.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(member))


def import_preset_archive(
    db: Session,
    *,
    storage: ObjectStorage,
    data: bytes,
) -> PresetImportReport:
    if len(data) > MAX_PRESET_ARCHIVE_BYTES:
        raise PresetError(
            "Preset archive is too large",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
            status_code=413,
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise PresetError(
            "Preset must be a .zip archive",
            code=ErrorCode.PRESET_INVALID_ARCHIVE,
        ) from exc
    with archive, tempfile.TemporaryDirectory(prefix="preset-") as tmp:
        target = Path(tmp)
        _safe_extract(archive, target)
        return import_preset_dir(db, storage=storage, root=_preset_root(target))


def import_preset_path(db: Session, *, storage: ObjectStorage, path: Path) -> PresetImportReport:
    if path.is_dir():
        return import_preset_dir(db, storage=storage, root=_preset_root(path))
    return import_preset_archive(db, storage=storage, data=path.read_bytes())
