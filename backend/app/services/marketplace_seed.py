"""Seed official free essentials pack + base search-tag vocabulary."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.marketplace import ESSENTIALS_PACK_SLUG, PackStatus
from app.core.mood_builtin_icons import MOOD_BUILTIN_ICONS
from app.core.mood_scale import DEFAULT_MOOD_SCORE_COLORS, MoodScore
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.icon_search_tag import IconSearchTag
from app.services.storage import ObjectStorage

# Repo root: backend/app/services -> parents[3] = mood-tracker
_FRONTEND_MOOD_ICONS = (
    Path(__file__).resolve().parents[3] / "frontend" / "public" / "mood-icons"
)

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


def main() -> None:
    from app.db.session import SessionLocal
    from app.services.storage import storage_service

    db = SessionLocal()
    try:
        pack = seed_essentials_pack(db, storage=storage_service)
        db.commit()
        print(f"Seeded pack slug={pack.slug} id={pack.id} icons={len(pack.icons)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
