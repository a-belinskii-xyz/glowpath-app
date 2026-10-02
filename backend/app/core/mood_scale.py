import re
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from app.core.i18n import LocaleLabels, resolve_label

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class MoodScoreIconType(StrEnum):
    EMOJI = "emoji"
    BUILTIN = "builtin"
    UPLOAD = "upload"
    CATALOG = "catalog"


class MoodScore(IntEnum):
    AWFUL = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    GREAT = 5


@dataclass(frozen=True, slots=True)
class MoodScoreMeta:
    labels: LocaleLabels
    emoji: str


@dataclass(frozen=True, slots=True)
class MoodScoreStyle:
    color: str
    icon_type: MoodScoreIconType
    icon: str


DEFAULT_MOOD_SCORE_COLORS: dict[MoodScore, str] = {
    MoodScore.AWFUL: "#ef4444",
    MoodScore.BAD: "#f97316",
    MoodScore.NEUTRAL: "#eab308",
    MoodScore.GOOD: "#22c55e",
    MoodScore.GREAT: "#3b82f6",
}

# Builtin face slugs (see mood_builtin_icons) used as the default scale icons.
DEFAULT_MOOD_SCORE_ICONS: dict[MoodScore, str] = {
    MoodScore.AWFUL: "face-awful-cry",
    MoodScore.BAD: "face-bad-sad",
    MoodScore.NEUTRAL: "face-neutral-flat",
    MoodScore.GOOD: "face-good-smile",
    MoodScore.GREAT: "face-great-grin",
}


MOOD_SCORE_META: dict[MoodScore, MoodScoreMeta] = {
    MoodScore.AWFUL: MoodScoreMeta(labels={"en": "awful", "ru": "ужасно"}, emoji="😢"),
    MoodScore.BAD: MoodScoreMeta(labels={"en": "bad", "ru": "плохо"}, emoji="😞"),
    MoodScore.NEUTRAL: MoodScoreMeta(labels={"en": "neutral", "ru": "нейтрально"}, emoji="😐"),
    MoodScore.GOOD: MoodScoreMeta(labels={"en": "good", "ru": "хорошо"}, emoji="🙂"),
    MoodScore.GREAT: MoodScoreMeta(labels={"en": "great", "ru": "отлично"}, emoji="😄"),
}

MIN_MOOD_SCORE = int(MoodScore.AWFUL)
MAX_MOOD_SCORE = int(MoodScore.GREAT)


def default_mood_score_style(score: MoodScore) -> MoodScoreStyle:
    return MoodScoreStyle(
        color=DEFAULT_MOOD_SCORE_COLORS[score],
        icon_type=MoodScoreIconType.BUILTIN,
        icon=DEFAULT_MOOD_SCORE_ICONS[score],
    )


def default_mood_score_styles() -> dict[str, MoodScoreStyle]:
    return {str(score.value): default_mood_score_style(score) for score in MoodScore}


def is_valid_hex_color(value: str) -> bool:
    return bool(_HEX_COLOR_RE.match(value))


def mood_score_label(score: MoodScore, locale: str) -> str:
    return resolve_label(MOOD_SCORE_META[score].labels, locale)


def resolve_mood_score_label(
    score: MoodScore,
    locale: str,
    overrides: dict[str, str] | None = None,
) -> str:
    """Return a custom label override when present, otherwise the locale default."""
    if overrides:
        custom = overrides.get(str(score.value))
        if isinstance(custom, str) and custom.strip():
            return custom.strip()
    return mood_score_label(score, locale)


def mood_score_emoji(score: MoodScore) -> str:
    return MOOD_SCORE_META[score].emoji
