"""Folder-based marketplace mock pack discovery and seed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.marketplace import PackStatus
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.services.marketplace_seed import (
    _marketplace_dir,
    discover_mock_packs,
    seed_mock_packs,
)
from app.services.storage import FakeStorage
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_discover_mock_packs_from_folders(tmp_path: Path) -> None:
    foxes = tmp_path / "Foxes"
    foxes.mkdir()
    (foxes / "Happy Fox.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (foxes / "pack.json").write_text(
        json.dumps(
            {
                "name": {"en": "Foxes", "ru": "Лисы"},
                "tags": ["animals"],
                "icons": {
                    "happy-fox": {
                        "labels": {"en": "Happy fox", "ru": "Весёлый лис"},
                        "scores": [5],
                        "colors": ["#f97316"],
                    }
                },
            }
        )
    )
    weather = tmp_path / "weather"
    weather.mkdir()
    (weather / "rain.png").write_bytes(b"png-bytes")
    (weather / "notes.txt").write_text("ignored")

    packs = discover_mock_packs(tmp_path)
    assert [pack.slug for pack in packs] == ["foxes", "weather"]

    fox_pack = packs[0]
    assert fox_pack.labels["name"] == {"en": "Foxes", "ru": "Лисы"}
    assert len(fox_pack.icons) == 1
    icon = fox_pack.icons[0]
    assert icon.slug == "happy-fox"
    assert icon.labels == {"en": "Happy fox", "ru": "Весёлый лис"}
    assert icon.tags == ("animals",)
    assert icon.colors == ("#f97316",)
    assert icon.scores == (5,)
    assert icon.mime_type == "image/svg+xml"

    weather_pack = packs[1]
    assert weather_pack.labels["name"]["en"] == "Weather"
    assert weather_pack.icons[0].slug == "rain"
    assert weather_pack.icons[0].mime_type == "image/png"
    assert weather_pack.icons[0].tags == ()
    assert weather_pack.icons[0].colors == ("#94a3b8",)
    assert weather_pack.price_tokens == 0
    assert weather_pack.published is True
    assert weather_pack.is_official is True
    assert weather_pack.cover_slug is None


def test_discover_skips_essentials_and_empty_folders(tmp_path: Path) -> None:
    reserved = tmp_path / "essentials"
    reserved.mkdir()
    (reserved / "x.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    empty = tmp_path / "empty-pack"
    empty.mkdir()
    (empty / "readme.txt").write_text("no images")
    assert discover_mock_packs(tmp_path) == ()


def test_discover_rejects_invalid_pack_json(tmp_path: Path) -> None:
    pack_dir = tmp_path / "broken"
    pack_dir.mkdir()
    (pack_dir / "icon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (pack_dir / "pack.json").write_text("{not-json")
    with pytest.raises(ValueError, match="pack.json"):
        discover_mock_packs(tmp_path)


def test_bundled_demo_mocks_are_discoverable() -> None:
    packs = discover_mock_packs(_marketplace_dir())
    demo = next(pack for pack in packs if pack.slug == "demo-mocks")
    slugs = {icon.slug for icon in demo.icons}
    assert slugs >= {
        "fox-happy",
        "fox-sad",
        "fox-dumbbell",
        "fox-sleep",
        "blob-joy",
        "star-burst",
        "rain-cloud",
        "coffee-cup",
    }
    happy = next(icon for icon in demo.icons if icon.slug == "fox-happy")
    assert happy.tags == ("joy", "animals")
    assert happy.scores == (4, 5)
    assert demo.price_tokens == 0
    assert demo.published is True
    assert demo.is_official is True
    assert demo.cover_slug == "fox-happy"


def test_seed_mock_packs_creates_and_refreshes(
    db: Session, storage: FakeStorage, tmp_path: Path
) -> None:
    pack_dir = tmp_path / "foxes"
    pack_dir.mkdir()
    svg_path = pack_dir / "happy.svg"
    svg_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' id='v1'/>")
    (pack_dir / "pack.json").write_text(
        json.dumps(
            {
                "name": {"en": "Foxes", "ru": "Лисы"},
                "icons": {"happy": {"tags": ["animals"], "colors": ["#f97316"]}},
            }
        )
    )

    first = seed_mock_packs(db, storage=storage, root=tmp_path)
    db.flush()
    assert len(first) == 1
    pack = db.scalar(select(IconPack).where(IconPack.slug == "foxes"))
    assert pack is not None
    assert pack.is_official is True
    assert pack.price_tokens == 0
    assert pack.labels["name"]["ru"] == "Лисы"
    icons = db.scalars(select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)).all()
    assert len(icons) == 1
    icon = icons[0]
    assert icon.slug == "happy"
    assert icon.suggested_colors == ["#f97316"]
    assert [tag.slug for tag in icon.search_tags] == ["animals"]
    assert storage.get_object(key=icon.storage_key) == svg_path.read_bytes()

    svg_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' id='v2'/>")
    seed_mock_packs(db, storage=storage, root=tmp_path)
    db.flush()
    refreshed = db.scalar(select(CatalogIcon).where(CatalogIcon.id == icon.id))
    assert refreshed is not None
    assert storage.get_object(key=refreshed.storage_key) == svg_path.read_bytes()
    remaining = db.scalars(select(CatalogIcon).where(CatalogIcon.pack_id == pack.id)).all()
    assert len(remaining) == 1


def test_pack_json_controls_price_availability_and_cover(
    db: Session, storage: FakeStorage, tmp_path: Path
) -> None:
    paid = tmp_path / "premium-foxes"
    paid.mkdir()
    (paid / "cover-fox.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' id='cover'/>")
    (paid / "extra-fox.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' id='extra'/>")
    (paid / "pack.json").write_text(
        json.dumps(
            {
                "slug": "fox-premium",
                "name": {"en": "Premium foxes", "ru": "Премиум-лисы"},
                "description": {"en": "Paid pack", "ru": "Платный пак"},
                "price_tokens": 50,
                "official": True,
                "published": True,
                "granted": False,
                "sort_order": 40,
                "cover": "cover-fox",
            }
        )
    )
    draft = tmp_path / "wip"
    draft.mkdir()
    (draft / "idea.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (draft / "pack.json").write_text(
        json.dumps(
            {
                "name": {"en": "WIP", "ru": "Черновик"},
                "published": False,
                "granted": True,
                "price_tokens": 99,
            }
        )
    )

    discovered = discover_mock_packs(tmp_path)
    by_slug = {pack.slug: pack for pack in discovered}
    assert by_slug["fox-premium"].price_tokens == 50
    assert by_slug["fox-premium"].published is True
    assert by_slug["fox-premium"].cover_slug == "cover-fox"
    assert by_slug["wip"].price_tokens == 0
    assert by_slug["wip"].published is False

    seed_mock_packs(db, storage=storage, root=tmp_path)
    db.flush()

    premium = db.scalar(select(IconPack).where(IconPack.slug == "fox-premium"))
    assert premium is not None
    assert premium.price_tokens == 50
    assert premium.status == PackStatus.PUBLISHED.value
    assert premium.is_official is True
    assert premium.sort_order == 40
    assert premium.published_at is not None
    cover = db.get(CatalogIcon, premium.cover_icon_id)
    assert cover is not None
    assert cover.slug == "cover-fox"

    wip = db.scalar(select(IconPack).where(IconPack.slug == "wip"))
    assert wip is not None
    assert wip.price_tokens == 0
    assert wip.status == PackStatus.DRAFT.value
    assert wip.published_at is None
