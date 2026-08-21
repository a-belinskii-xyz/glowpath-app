"""Seed official free essentials pack + base search-tag vocabulary."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.marketplace import DEMO_MOCKS_PACK_SLUG, ESSENTIALS_PACK_SLUG, PackStatus
from app.core.mood_builtin_icons import MOOD_BUILTIN_ICONS
from app.core.mood_scale import DEFAULT_MOOD_SCORE_COLORS, MoodScore
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.icon_search_tag import IconSearchTag
from app.services.storage import ObjectStorage

# Repo root: backend/app/services -> parents[3] = mood-tracker (host layout)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # backend/app (also /app/app in Docker)
_FRONTEND_MOOD_ICONS = _REPO_ROOT / "frontend" / "public" / "mood-icons"
_MARKETPLACE_MOCKS_CANDIDATES = (
    _REPO_ROOT / "frontend" / "public" / "marketplace-mocks",
    _PACKAGE_ROOT / "data" / "marketplace_mocks",
)


def _marketplace_mocks_dir() -> Path:
    for candidate in _MARKETPLACE_MOCKS_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return _MARKETPLACE_MOCKS_CANDIDATES[-1]


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
_BUILTIN_META: dict[str, dict] = {
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

_DEMO_MOCK_ICONS: list[dict] = [
    {
        "slug": "fox-happy",
        "file": "fox-happy.svg",
        "labels": {"en": "Happy fox", "ru": "Весёлый лис"},
        "tags": ["joy", "animals"],
        "colors": ["#f97316", "#f59e0b"],
        "scores": [4, 5],
    },
    {
        "slug": "fox-sad",
        "file": "fox-sad.svg",
        "labels": {"en": "Sad fox", "ru": "Грустный лис"},
        "tags": ["sadness", "animals"],
        "colors": ["#2563eb", "#60a5fa"],
        "scores": [1, 2],
    },
    {
        "slug": "fox-dumbbell",
        "file": "fox-dumbbell.svg",
        "labels": {"en": "Fox with dumbbells", "ru": "Лис с гантелями"},
        "tags": ["sport", "fitness", "animals"],
        "colors": ["#16a34a", "#84cc16"],
        "scores": [4, 5],
    },
    {
        "slug": "fox-sleep",
        "file": "fox-sleep.svg",
        "labels": {"en": "Sleepy fox", "ru": "Сонный лис"},
        "tags": ["night", "calm", "animals"],
        "colors": ["#7c3aed", "#a78bfa"],
        "scores": [3],
    },
    {
        "slug": "blob-joy",
        "file": "blob-joy.svg",
        "labels": {"en": "Joy blob", "ru": "Радостный блоб"},
        "tags": ["joy", "energy"],
        "colors": ["#db2777", "#f472b6"],
        "scores": [5],
    },
    {
        "slug": "star-burst",
        "file": "star-burst.svg",
        "labels": {"en": "Star burst", "ru": "Вспышка звезды"},
        "tags": ["joy", "energy"],
        "colors": ["#d97706", "#eab308"],
        "scores": [4, 5],
    },
    {
        "slug": "rain-cloud",
        "file": "rain-cloud.svg",
        "labels": {"en": "Rain cloud", "ru": "Дождевое облако"},
        "tags": ["sadness", "weather"],
        "colors": ["#64748b", "#94a3b8"],
        "scores": [1, 2],
    },
    {
        "slug": "coffee-cup",
        "file": "coffee-cup.svg",
        "labels": {"en": "Coffee cup", "ru": "Чашка кофе"},
        "tags": ["calm", "energy"],
        "colors": ["#dc2626", "#f97316"],
        "scores": [3, 4],
    },
]


def seed_default_search_tags(db: Session) -> list[IconSearchTag]:
    existing = {
        tag.slug: tag
        for tag in db.scalars(select(IconSearchTag)).all()
    }
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
    tags_by_slug = {
        tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()
    }

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
        for icon in db.scalars(
            select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)
        ).all()
    }

    cover_id = pack.cover_icon_id
    for index, builtin in enumerate(MOOD_BUILTIN_ICONS.values()):
        meta = _BUILTIN_META.get(builtin.slug, {"tags": [], "colors": ["#94a3b8"]})
        asset_name = Path(builtin.asset_path).name
        svg_path = _FRONTEND_MOOD_ICONS / asset_name
        if not svg_path.is_file():
            continue
        data = svg_path.read_bytes()
        scores = (
            [builtin.default_score.value]
            if builtin.default_score is not None
            else []
        )
        icon = existing_icons.get(builtin.slug)
        if icon is None:
            import uuid

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

        icon.search_tags = [
            tags_by_slug[slug] for slug in meta["tags"] if slug in tags_by_slug
        ]
        if cover_id is None:
            cover_id = icon.id

    pack.cover_icon_id = cover_id
    if pack.published_at is None:
        from datetime import datetime, timezone

        pack.published_at = datetime.now(timezone.utc)
    db.flush()
    return pack


def seed_demo_mocks_pack(db: Session, *, storage: ObjectStorage) -> IconPack:
    """Idempotent seed of temporary mock icons from frontend/public/marketplace-mocks."""
    seed_default_search_tags(db)
    tags_by_slug = {
        tag.slug: tag for tag in db.scalars(select(IconSearchTag)).all()
    }

    pack = db.scalar(select(IconPack).where(IconPack.slug == DEMO_MOCKS_PACK_SLUG))
    if pack is None:
        pack = IconPack(
            slug=DEMO_MOCKS_PACK_SLUG,
            author_id=None,
            is_official=True,
            status=PackStatus.PUBLISHED.value,
            price_tokens=0,
            labels={
                "name": {"en": "Demo mocks", "ru": "Демо-моки"},
                "description": {
                    "en": "Temporary placeholder icons — replace files in marketplace-mocks/.",
                    "ru": "Временные заглушки — замените файлы в marketplace-mocks/.",
                },
            },
            sort_order=10,
        )
        db.add(pack)
        db.flush()
    else:
        pack.is_official = True
        pack.status = PackStatus.PUBLISHED.value
        pack.price_tokens = 0

    existing_icons = {
        icon.slug: icon
        for icon in db.scalars(
            select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)
        ).all()
    }

    import uuid
    from datetime import datetime, timezone

    cover_id = pack.cover_icon_id
    for index, item in enumerate(_DEMO_MOCK_ICONS):
        svg_path = _marketplace_mocks_dir() / item["file"]
        if not svg_path.is_file():
            continue
        data = svg_path.read_bytes()
        icon = existing_icons.get(item["slug"])
        if icon is None:
            icon_id = uuid.uuid4()
            storage_key = f"catalog/{pack.id}/{icon_id}_{item['file']}"
            storage.put_object(
                key=storage_key,
                data=data,
                content_type="image/svg+xml",
            )
            icon = CatalogIcon(
                id=icon_id,
                pack_id=pack.id,
                slug=item["slug"],
                labels=dict(item["labels"]),
                storage_key=storage_key,
                mime_type="image/svg+xml",
                size_bytes=len(data),
                suggested_colors=list(item["colors"]),
                suggested_mood_scores=list(item["scores"]),
                sort_order=index,
            )
            db.add(icon)
            db.flush()
        else:
            # Refresh bytes so replacing SVG files on disk is picked up on re-seed.
            storage.put_object(
                key=icon.storage_key,
                data=data,
                content_type="image/svg+xml",
            )
            icon.labels = dict(item["labels"])
            icon.mime_type = "image/svg+xml"
            icon.size_bytes = len(data)
            icon.suggested_colors = list(item["colors"])
            icon.suggested_mood_scores = list(item["scores"])
            icon.sort_order = index

        icon.search_tags = [
            tags_by_slug[slug] for slug in item["tags"] if slug in tags_by_slug
        ]
        if cover_id is None:
            cover_id = icon.id

    if not any(
        (_marketplace_mocks_dir() / item["file"]).is_file() for item in _DEMO_MOCK_ICONS
    ):
        raise FileNotFoundError(
            f"No demo mock SVGs found under {_marketplace_mocks_dir()}"
        )

    pack.cover_icon_id = cover_id
    if pack.published_at is None:
        pack.published_at = datetime.now(timezone.utc)
    db.flush()
    return pack


def seed_marketplace_catalog(db: Session, *, storage: ObjectStorage) -> list[IconPack]:
    essentials = seed_essentials_pack(db, storage=storage)
    demo = seed_demo_mocks_pack(db, storage=storage)
    return [essentials, demo]


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
