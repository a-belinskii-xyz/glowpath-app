from __future__ import annotations

from dataclasses import dataclass

from app.core.i18n import LocaleLabels
from app.core.mood_scale import MoodScore


@dataclass(frozen=True, slots=True)
class BuiltinMoodIcon:
    slug: str
    labels: LocaleLabels
    asset_path: str
    default_score: MoodScore | None = None


MOOD_BUILTIN_ICONS: dict[str, BuiltinMoodIcon] = {
    "awful-cloud": BuiltinMoodIcon(
        slug="awful-cloud",
        labels={"en": "Rain cloud", "ru": "Дождливая туча"},
        asset_path="/mood-icons/awful-cloud.svg",
        default_score=MoodScore.AWFUL,
    ),
    "bad-droplet": BuiltinMoodIcon(
        slug="bad-droplet",
        labels={"en": "Droplet", "ru": "Капля"},
        asset_path="/mood-icons/bad-droplet.svg",
        default_score=MoodScore.BAD,
    ),
    "neutral-line": BuiltinMoodIcon(
        slug="neutral-line",
        labels={"en": "Flat line", "ru": "Ровная линия"},
        asset_path="/mood-icons/neutral-line.svg",
        default_score=MoodScore.NEUTRAL,
    ),
    "good-sun": BuiltinMoodIcon(
        slug="good-sun",
        labels={"en": "Sun", "ru": "Солнце"},
        asset_path="/mood-icons/good-sun.svg",
        default_score=MoodScore.GOOD,
    ),
    "great-star": BuiltinMoodIcon(
        slug="great-star",
        labels={"en": "Star", "ru": "Звезда"},
        asset_path="/mood-icons/great-star.svg",
        default_score=MoodScore.GREAT,
    ),
    "heart": BuiltinMoodIcon(
        slug="heart",
        labels={"en": "Heart", "ru": "Сердце"},
        asset_path="/mood-icons/heart.svg",
    ),
    "leaf": BuiltinMoodIcon(
        slug="leaf",
        labels={"en": "Leaf", "ru": "Лист"},
        asset_path="/mood-icons/leaf.svg",
    ),
    "fire": BuiltinMoodIcon(
        slug="fire",
        labels={"en": "Fire", "ru": "Огонь"},
        asset_path="/mood-icons/fire.svg",
    ),
    "moon": BuiltinMoodIcon(
        slug="moon",
        labels={"en": "Moon", "ru": "Луна"},
        asset_path="/mood-icons/moon.svg",
    ),
    "sparkles": BuiltinMoodIcon(
        slug="sparkles",
        labels={"en": "Sparkles", "ru": "Искры"},
        asset_path="/mood-icons/sparkles.svg",
    ),
}


def is_valid_builtin_icon_slug(slug: str) -> bool:
    return slug in MOOD_BUILTIN_ICONS


def default_builtin_slug_for_score(score: MoodScore) -> str:
    for icon in MOOD_BUILTIN_ICONS.values():
        if icon.default_score == score:
            return icon.slug
    return "neutral-line"
