import re
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from app.core.i18n import LocaleLabels, resolve_label

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class MoodScoreIconType(StrEnum):
    EMOJI = "emoji"
    BUILTIN = "builtin"
    UPLOAD = "upload"


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
    MoodScore.AWFUL: "#64748b",
    MoodScore.BAD: "#94a3b8",
    MoodScore.NEUTRAL: "#60a5fa",
    MoodScore.GOOD: "#34d399",
    MoodScore.GREAT: "#f59e0b",
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
        icon_type=MoodScoreIconType.EMOJI,
        icon=mood_score_emoji(score),
    )


def default_mood_score_styles() -> dict[str, MoodScoreStyle]:
    return {str(score.value): default_mood_score_style(score) for score in MoodScore}


def is_valid_hex_color(value: str) -> bool:
    return bool(_HEX_COLOR_RE.match(value))


def mood_score_label(score: MoodScore, locale: str) -> str:
    return resolve_label(MOOD_SCORE_META[score].labels, locale)


def mood_score_emoji(score: MoodScore) -> str:
    return MOOD_SCORE_META[score].emoji
