from __future__ import annotations

from dataclasses import dataclass

from app.core.i18n import LocaleLabels
from app.core.mood_scale import DEFAULT_MOOD_SCORE_ICONS, MoodScore


@dataclass(frozen=True, slots=True)
class BuiltinMoodIcon:
    slug: str
    labels: LocaleLabels
    asset_path: str
    suggested_score: MoodScore | None = None


MOOD_BUILTIN_ICONS: dict[str, BuiltinMoodIcon] = {
    "face-awful-cry": BuiltinMoodIcon(
        slug="face-awful-cry",
        labels={"en": "Crying", "ru": "Плачу"},
        asset_path="/mood-icons/face-awful-cry.svg",
        suggested_score=MoodScore.AWFUL,
    ),
    "face-awful-angry": BuiltinMoodIcon(
        slug="face-awful-angry",
        labels={"en": "Angry", "ru": "Злюсь"},
        asset_path="/mood-icons/face-awful-angry.svg",
        suggested_score=MoodScore.AWFUL,
    ),
    "face-awful-storm": BuiltinMoodIcon(
        slug="face-awful-storm",
        labels={"en": "Overwhelmed", "ru": "Накрыло"},
        asset_path="/mood-icons/face-awful-storm.svg",
        suggested_score=MoodScore.AWFUL,
    ),
    "face-bad-sad": BuiltinMoodIcon(
        slug="face-bad-sad",
        labels={"en": "Sad", "ru": "Грустно"},
        asset_path="/mood-icons/face-bad-sad.svg",
        suggested_score=MoodScore.BAD,
    ),
    "face-bad-tired": BuiltinMoodIcon(
        slug="face-bad-tired",
        labels={"en": "Tired", "ru": "Без сил"},
        asset_path="/mood-icons/face-bad-tired.svg",
        suggested_score=MoodScore.BAD,
    ),
    "face-bad-worried": BuiltinMoodIcon(
        slug="face-bad-worried",
        labels={"en": "Worried", "ru": "Тревожно"},
        asset_path="/mood-icons/face-bad-worried.svg",
        suggested_score=MoodScore.BAD,
    ),
    "face-neutral-flat": BuiltinMoodIcon(
        slug="face-neutral-flat",
        labels={"en": "Neutral", "ru": "Ровно"},
        asset_path="/mood-icons/face-neutral-flat.svg",
        suggested_score=MoodScore.NEUTRAL,
    ),
    "face-neutral-side": BuiltinMoodIcon(
        slug="face-neutral-side",
        labels={"en": "Unsure", "ru": "Так себе"},
        asset_path="/mood-icons/face-neutral-side.svg",
        suggested_score=MoodScore.NEUTRAL,
    ),
    "face-neutral-calm": BuiltinMoodIcon(
        slug="face-neutral-calm",
        labels={"en": "Calm", "ru": "Спокойно"},
        asset_path="/mood-icons/face-neutral-calm.svg",
        suggested_score=MoodScore.NEUTRAL,
    ),
    "face-good-smile": BuiltinMoodIcon(
        slug="face-good-smile",
        labels={"en": "Smile", "ru": "Улыбка"},
        asset_path="/mood-icons/face-good-smile.svg",
        suggested_score=MoodScore.GOOD,
    ),
    "face-good-wink": BuiltinMoodIcon(
        slug="face-good-wink",
        labels={"en": "Wink", "ru": "Подмигиваю"},
        asset_path="/mood-icons/face-good-wink.svg",
        suggested_score=MoodScore.GOOD,
    ),
    "face-good-blush": BuiltinMoodIcon(
        slug="face-good-blush",
        labels={"en": "Pleased", "ru": "Приятно"},
        asset_path="/mood-icons/face-good-blush.svg",
        suggested_score=MoodScore.GOOD,
    ),
    "face-great-grin": BuiltinMoodIcon(
        slug="face-great-grin",
        labels={"en": "Laughing", "ru": "Смеюсь"},
        asset_path="/mood-icons/face-great-grin.svg",
        suggested_score=MoodScore.GREAT,
    ),
    "face-great-stars": BuiltinMoodIcon(
        slug="face-great-stars",
        labels={"en": "Starstruck", "ru": "В восторге"},
        asset_path="/mood-icons/face-great-stars.svg",
        suggested_score=MoodScore.GREAT,
    ),
    "face-great-love": BuiltinMoodIcon(
        slug="face-great-love",
        labels={"en": "In love", "ru": "Любовь"},
        asset_path="/mood-icons/face-great-love.svg",
        suggested_score=MoodScore.GREAT,
    ),
    "awful-cloud": BuiltinMoodIcon(
        slug="awful-cloud",
        labels={"en": "Rain cloud", "ru": "Дождливая туча"},
        asset_path="/mood-icons/awful-cloud.svg",
        suggested_score=MoodScore.AWFUL,
    ),
    "bad-droplet": BuiltinMoodIcon(
        slug="bad-droplet",
        labels={"en": "Droplet", "ru": "Капля"},
        asset_path="/mood-icons/bad-droplet.svg",
        suggested_score=MoodScore.BAD,
    ),
    "neutral-line": BuiltinMoodIcon(
        slug="neutral-line",
        labels={"en": "Flat line", "ru": "Ровная линия"},
        asset_path="/mood-icons/neutral-line.svg",
        suggested_score=MoodScore.NEUTRAL,
    ),
    "good-sun": BuiltinMoodIcon(
        slug="good-sun",
        labels={"en": "Sun", "ru": "Солнце"},
        asset_path="/mood-icons/good-sun.svg",
        suggested_score=MoodScore.GOOD,
    ),
    "great-star": BuiltinMoodIcon(
        slug="great-star",
        labels={"en": "Star", "ru": "Звезда"},
        asset_path="/mood-icons/great-star.svg",
        suggested_score=MoodScore.GREAT,
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
    return DEFAULT_MOOD_SCORE_ICONS[score]
