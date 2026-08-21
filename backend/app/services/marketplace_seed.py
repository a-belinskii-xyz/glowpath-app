"""Seed official free essentials pack + folder-based mock packs."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.marketplace import (
    ESSENTIALS_PACK_SLUG,
    MAX_CATALOG_ICON_BYTES,
    MAX_SUGGESTED_COLORS,
    PackStatus,
)
from app.core.mood_builtin_icons import MOOD_BUILTIN_ICONS
from app.core.mood_scale import DEFAULT_MOOD_SCORE_COLORS, MoodScore, is_valid_hex_color
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.icon_search_tag import IconSearchTag
from app.services.storage import ObjectStorage

# Repo root: backend/app/services -> parents[3] = mood-tracker (host layout)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # backend/app (also /app/app in Docker)
_FRONTEND_MOOD_ICONS = _REPO_ROOT / "frontend" / "public" / "mood-icons"
_MARKETPLACE_DIR = _PACKAGE_ROOT / "data" / "marketplace"
_PACK_META_FILENAME = "pack.json"
_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")
_IMAGE_MIME_BY_SUFFIX: dict[str, str] = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_DEFAULT_ICON_COLOR = "#94a3b8"


def _marketplace_dir() -> Path:
    return _MARKETPLACE_DIR


DEFAULT_SEARCH_TAGS: list[tuple[str, dict[str, str], int]] = [
    ("joy", {"en": "Joy", "ru": "Радость"}, 10),
    ("sadness", {"en": "Sadness", "ru": "Грусть"}, 20),
    ("calm", {"en": "Calm", "ru": "Спокойствие"}, 30),
    ("energy", {"en": "Energy", "ru": "Энергия"}, 40),
    ("sport", {"en": "Sport", "ru": "Спорт"}, 50),
    ("fitness", {"en": "Fitness", "ru": "Фитнес"}, 60),
    ("animals", {"en": "Animals", "ru": "Животные"}, 70),
    ("nature", {"en": "Nature", "ru": "Природа"}, 80),
    ("weather", {"en": "Weather", "ru": "Погода"}, 90),
    ("night", {"en": "Night", "ru": "Ночь"}, 100),
]

# Suggested search tags + colors for each builtin slug
_BUILTIN_META: dict[str, dict[str, list[str]]] = {
    "awful-cloud": {
        "tags": ["sadness", "weather"],
        "colors": [DEFAULT_MOOD_SCORE_COLORS[MoodScore.AWFUL], "#94a3b8"],
    },
    "bad-droplet": {
        "tags": ["sadness", "weather"],
        "colors": [DEFAULT_MOOD_SCORE_COLORS[MoodScore.BAD], "#60a5fa"],
    },
    "neutral-line": {
        "tags": ["calm"],
        "colors": [DEFAULT_MOOD_SCORE_COLORS[MoodScore.NEUTRAL], "#94a3b8"],
    },
    "good-sun": {
        "tags": ["joy", "weather"],
        "colors": [DEFAULT_MOOD_SCORE_COLORS[MoodScore.GOOD], "#f59e0b"],
    },
    "great-star": {
        "tags": ["joy", "energy"],
        "colors": [DEFAULT_MOOD_SCORE_COLORS[MoodScore.GREAT], "#eab308"],
    },
    "heart": {
        "tags": ["joy"],
        "colors": ["#f472b6", "#ef4444"],
    },
    "leaf": {
        "tags": ["nature", "calm"],
        "colors": ["#34d399", "#84cc16"],
    },
    "fire": {
        "tags": ["energy"],
        "colors": ["#f97316", "#ef4444"],
    },
    "moon": {
        "tags": ["night", "calm"],
        "colors": ["#a78bfa", "#60a5fa"],
    },
    "sparkles": {
        "tags": ["joy", "energy"],
        "colors": ["#eab308", "#a78bfa"],
    },
}


@dataclass(frozen=True, slots=True)
class DiscoveredMockIcon:
    slug: str
    path: Path
    file_name: str
    mime_type: str
    labels: dict[str, str]
    tags: tuple[str, ...]
    colors: tuple[str, ...]
    scores: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DiscoveredMockPack:
    slug: str
    labels: dict[str, dict[str, str]]
    price_tokens: int
    sort_order: int
    is_official: bool
    published: bool
    cover_slug: str | None
    icons: tuple[DiscoveredMockIcon, ...]


def _slugify(raw: str) -> str:
    slug = _SLUGIFY_RE.sub("-", raw.lower()).strip("-")
    if not slug:
        slug = "item"
    if not slug[0].isalpha():
        slug = f"p-{slug}"
    return slug[:64]


def _title_from_slug(slug: str) -> str:
    words = [part for part in slug.replace("_", "-").split("-") if part]
    if not words:
        return slug
    return " ".join(word.capitalize() if index == 0 else word for index, word in enumerate(words))


def _locale_labels(raw: object, *, fallback: str) -> dict[str, str]:
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()[:200]
        return {"en": text, "ru": text}
    if isinstance(raw, dict) and raw:
        labels: dict[str, str] = {}
        for locale, value in raw.items():
            if isinstance(locale, str) and isinstance(value, str) and value.strip():
                labels[locale.strip().lower()[:16]] = value.strip()[:200]
        if labels:
            return labels
    return {"en": fallback, "ru": fallback}


def _string_tuple(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        slug = item.strip().lower()
        if slug and slug not in seen:
            seen.add(slug)
            values.append(slug)
    return tuple(values)


def _color_tuple(raw: object, *, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return fallback
    colors = tuple(
        item.strip() for item in raw if isinstance(item, str) and is_valid_hex_color(item.strip())
    )
    return colors[:MAX_SUGGESTED_COLORS] or fallback


def _score_tuple(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return ()
    scores: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            continue
        if 1 <= item <= 5 and item not in scores:
            scores.append(item)
    return tuple(scores)


def _non_negative_int(raw: object, *, default: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return default
    return max(raw, 0)


def _bool(raw: object, *, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _optional_slug(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _slugify(Path(raw.strip()).stem)


def _first_present(meta: dict[str, object], *keys: str) -> object:
    for key in keys:
        if key in meta:
            return meta[key]
    return None


def _load_pack_json(pack_dir: Path) -> dict[str, object]:
    meta_path = pack_dir / _PACK_META_FILENAME
    if not meta_path.is_file():
        return {}
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {meta_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{meta_path} must be a JSON object")
    return {str(key): value for key, value in raw.items()}


def _icon_override(pack_meta: dict[str, object], *, slug: str, file_name: str) -> dict[str, object]:
    icons = pack_meta.get("icons")
    if not isinstance(icons, dict):
        return {}
    for key in (slug, file_name, Path(file_name).stem):
        value = icons.get(key)
        if isinstance(value, dict):
            return {str(item_key): item_value for item_key, item_value in value.items()}
    return {}


def _discover_icons(pack_dir: Path, pack_meta: dict[str, object]) -> tuple[DiscoveredMockIcon, ...]:
    default_tags = _string_tuple(pack_meta.get("tags"))
    default_colors = _color_tuple(pack_meta.get("colors"), fallback=(_DEFAULT_ICON_COLOR,))
    icons: list[DiscoveredMockIcon] = []
    used_slugs: set[str] = set()
    for path in sorted(pack_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        mime_type = _IMAGE_MIME_BY_SUFFIX.get(path.suffix.lower())
        if mime_type is None:
            continue
        slug = _slugify(path.stem)
        if slug in used_slugs:
            continue
        size = path.stat().st_size
        if size == 0 or size > MAX_CATALOG_ICON_BYTES:
            print(f"Skipping {path}: empty or larger than {MAX_CATALOG_ICON_BYTES} bytes")
            continue
        used_slugs.add(slug)
        override = _icon_override(pack_meta, slug=slug, file_name=path.name)
        title = _title_from_slug(slug)
        icons.append(
            DiscoveredMockIcon(
                slug=slug,
                path=path,
                file_name=path.name,
                mime_type=mime_type,
                labels=_locale_labels(override.get("labels"), fallback=title),
                tags=_string_tuple(override.get("tags")) or default_tags,
                colors=_color_tuple(override.get("colors"), fallback=default_colors),
                scores=_score_tuple(override.get("scores")),
            )
        )
    return tuple(icons)


def discover_mock_packs(root: Path) -> tuple[DiscoveredMockPack, ...]:
    """Each subdirectory of `root` becomes a pack; image files inside become icons."""
    if not root.is_dir():
        return ()
    packs: list[DiscoveredMockPack] = []
    used_slugs: set[str] = {ESSENTIALS_PACK_SLUG}
    folders = sorted(
        (path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda path: path.name.lower(),
    )
    auto_sort = 10
    for folder in folders:
        meta = _load_pack_json(folder)
        slug = _optional_slug(meta.get("slug")) or _slugify(folder.name)
        if slug in used_slugs:
            print(f"Skipping mock pack folder {folder.name}: reserved or duplicate slug {slug}")
            continue
        icons = _discover_icons(folder, meta)
        if not icons:
            continue
        used_slugs.add(slug)
        title = _title_from_slug(slug)
        raw_sort = meta.get("sort_order")
        if isinstance(raw_sort, int) and not isinstance(raw_sort, bool):
            sort_order = raw_sort
        else:
            sort_order = auto_sort
            auto_sort += 10
        price_tokens = _non_negative_int(_first_present(meta, "price_tokens", "price"), default=0)
        raw_granted = _first_present(meta, "granted", "unlocked", "available")
        granted = _bool(raw_granted, default=price_tokens == 0)
        raw_status = meta.get("status")
        if isinstance(raw_status, str) and raw_status.strip().lower() in {
            PackStatus.DRAFT.value,
            PackStatus.PUBLISHED.value,
            PackStatus.ARCHIVED.value,
        }:
            published = raw_status.strip().lower() == PackStatus.PUBLISHED.value
        else:
            published = _bool(meta.get("published"), default=True)
        packs.append(
            DiscoveredMockPack(
                slug=slug,
                labels={
                    "name": _locale_labels(meta.get("name"), fallback=title),
                    "description": _locale_labels(
                        meta.get("description"),
                        fallback=f"Icons from marketplace/{folder.name}/.",
                    ),
                },
                price_tokens=0 if granted else price_tokens,
                sort_order=sort_order,
                is_official=_bool(_first_present(meta, "official", "is_official"), default=True),
                published=published,
                cover_slug=_optional_slug(_first_present(meta, "cover", "cover_icon")),
                icons=icons,
            )
        )
    return tuple(packs)


def seed_default_search_tags(db: Session) -> list[IconSearchTag]:
    existing = {tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()}
    created: list[IconSearchTag] = []
    for slug, labels, sort_order in DEFAULT_SEARCH_TAGS:
        if slug in existing:
            created.append(existing[slug])
            continue
        tag = IconSearchTag(slug=slug, labels=labels, sort_order=sort_order, is_active=True)
        db.add(tag)
        created.append(tag)
    db.flush()
    return created


def seed_essentials_pack(db: Session, *, storage: ObjectStorage) -> IconPack:
    """Idempotent seed of the free official essentials pack from builtin SVGs."""
    seed_default_search_tags(db)
    tags_by_slug = {tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()}

    pack = db.scalar(select(IconPack).where(IconPack.slug == ESSENTIALS_PACK_SLUG))
    if pack is None:
        pack = IconPack(
            slug=ESSENTIALS_PACK_SLUG,
            author_id=None,
            is_official=True,
            status=PackStatus.PUBLISHED.value,
            price_tokens=0,
            labels={
                "name": {"en": "Essentials", "ru": "Базовый"},
                "description": {
                    "en": "Free starter icons for moods, tags, and goals.",
                    "ru": "Бесплатный стартовый набор иконок для настроения, тегов и целей.",
                },
            },
            sort_order=0,
        )
        db.add(pack)
        db.flush()
    else:
        pack.is_official = True
        pack.status = PackStatus.PUBLISHED.value
        pack.price_tokens = 0

    existing_icons = {
        icon.slug: icon
        for icon in db.scalars(select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)).all()
    }

    cover_id = pack.cover_icon_id
    for index, builtin in enumerate(MOOD_BUILTIN_ICONS.values()):
        meta = _BUILTIN_META.get(builtin.slug, {"tags": [], "colors": ["#94a3b8"]})
        asset_name = Path(builtin.asset_path).name
        svg_path = _FRONTEND_MOOD_ICONS / asset_name
        if not svg_path.is_file():
            continue
        data = svg_path.read_bytes()
        scores = [builtin.default_score.value] if builtin.default_score is not None else []
        icon = existing_icons.get(builtin.slug)
        if icon is None:
            icon_id = uuid.uuid4()
            storage_key = f"catalog/{pack.id}/{icon_id}_{asset_name}"
            storage.put_object(
                key=storage_key,
                data=data,
                content_type="image/svg+xml",
            )
            icon = CatalogIcon(
                id=icon_id,
                pack_id=pack.id,
                slug=builtin.slug,
                labels=dict(builtin.labels),
                storage_key=storage_key,
                mime_type="image/svg+xml",
                size_bytes=len(data),
                suggested_colors=list(meta["colors"]),
                suggested_mood_scores=scores,
                sort_order=index,
            )
            db.add(icon)
            db.flush()
        else:
            icon.labels = dict(builtin.labels)
            icon.suggested_colors = list(meta["colors"])
            icon.suggested_mood_scores = scores
            icon.sort_order = index

        icon.search_tags = [tags_by_slug[slug] for slug in meta["tags"] if slug in tags_by_slug]
        if cover_id is None:
            cover_id = icon.id

    pack.cover_icon_id = cover_id
    if pack.published_at is None:
        pack.published_at = datetime.now(UTC)
    db.flush()
    return pack


def _seed_one_mock_pack(
    db: Session,
    *,
    storage: ObjectStorage,
    folder: DiscoveredMockPack,
    tags_by_slug: dict[str, IconSearchTag],
) -> IconPack:
    status = PackStatus.PUBLISHED.value if folder.published else PackStatus.DRAFT.value
    pack = db.scalar(select(IconPack).where(IconPack.slug == folder.slug))
    if pack is None:
        pack = IconPack(
            slug=folder.slug,
            author_id=None,
            is_official=folder.is_official,
            status=status,
            price_tokens=folder.price_tokens,
            labels=folder.labels,
            sort_order=folder.sort_order,
        )
        db.add(pack)
        db.flush()
    else:
        pack.is_official = folder.is_official
        pack.status = status
        pack.price_tokens = folder.price_tokens
        pack.labels = folder.labels
        pack.sort_order = folder.sort_order

    existing_icons = {
        icon.slug: icon
        for icon in db.scalars(select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)).all()
    }

    seeded_icons: dict[str, CatalogIcon] = {}
    for index, item in enumerate(folder.icons):
        data = item.path.read_bytes()
        icon = existing_icons.get(item.slug)
        if icon is None:
            icon_id = uuid.uuid4()
            storage_key = f"catalog/{pack.id}/{icon_id}_{item.file_name}"
            storage.put_object(
                key=storage_key,
                data=data,
                content_type=item.mime_type,
            )
            icon = CatalogIcon(
                id=icon_id,
                pack_id=pack.id,
                slug=item.slug,
                labels=dict(item.labels),
                storage_key=storage_key,
                mime_type=item.mime_type,
                size_bytes=len(data),
                suggested_colors=list(item.colors),
                suggested_mood_scores=list(item.scores),
                sort_order=index,
            )
            db.add(icon)
            db.flush()
        else:
            storage.put_object(
                key=icon.storage_key,
                data=data,
                content_type=item.mime_type,
            )
            icon.labels = dict(item.labels)
            icon.mime_type = item.mime_type
            icon.size_bytes = len(data)
            icon.suggested_colors = list(item.colors)
            icon.suggested_mood_scores = list(item.scores)
            icon.sort_order = index

        icon.search_tags = [tags_by_slug[slug] for slug in item.tags if slug in tags_by_slug]
        seeded_icons[item.slug] = icon

    if folder.cover_slug and folder.cover_slug in seeded_icons:
        pack.cover_icon_id = seeded_icons[folder.cover_slug].id
    elif pack.cover_icon_id is None and folder.icons:
        pack.cover_icon_id = seeded_icons[folder.icons[0].slug].id
    if folder.published:
        if pack.published_at is None:
            pack.published_at = datetime.now(UTC)
    else:
        pack.published_at = None
    db.flush()
    return pack


def seed_mock_packs(
    db: Session,
    *,
    storage: ObjectStorage,
    root: Path | None = None,
) -> list[IconPack]:
    """Idempotent seed: each folder under data/marketplace/ becomes a published pack."""
    seed_default_search_tags(db)
    tags_by_slug = {tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()}
    return [
        _seed_one_mock_pack(db, storage=storage, folder=folder, tags_by_slug=tags_by_slug)
        for folder in discover_mock_packs(root or _marketplace_dir())
    ]


def seed_marketplace_catalog(db: Session, *, storage: ObjectStorage) -> list[IconPack]:
    essentials = seed_essentials_pack(db, storage=storage)
    mocks = seed_mock_packs(db, storage=storage)
    return [essentials, *mocks]


def main() -> None:
    from app.db.session import SessionLocal
    from app.services.storage import storage_service

    db = SessionLocal()
    try:
        packs = seed_marketplace_catalog(db, storage=storage_service)
        db.commit()
        for pack in packs:
            print(f"Seeded pack slug={pack.slug} id={pack.id} icons={len(pack.icons)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
