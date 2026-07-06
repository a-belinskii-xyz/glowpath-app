from dataclasses import dataclass
from enum import IntEnum

from app.core.i18n import LocaleLabels, resolve_label


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


MOOD_SCORE_META: dict[MoodScore, MoodScoreMeta] = {
    MoodScore.AWFUL: MoodScoreMeta(labels={"en": "awful", "ru": "ужасно"}, emoji="😢"),
    MoodScore.BAD: MoodScoreMeta(labels={"en": "bad", "ru": "плохо"}, emoji="😞"),
    MoodScore.NEUTRAL: MoodScoreMeta(labels={"en": "neutral", "ru": "нейтрально"}, emoji="😐"),
    MoodScore.GOOD: MoodScoreMeta(labels={"en": "good", "ru": "хорошо"}, emoji="🙂"),
    MoodScore.GREAT: MoodScoreMeta(labels={"en": "great", "ru": "отлично"}, emoji="😄"),
}

MIN_MOOD_SCORE = int(MoodScore.AWFUL)
MAX_MOOD_SCORE = int(MoodScore.GREAT)


def mood_score_label(score: MoodScore, locale: str) -> str:
    return resolve_label(MOOD_SCORE_META[score].labels, locale)


def mood_score_emoji(score: MoodScore) -> str:
    return MOOD_SCORE_META[score].emoji
