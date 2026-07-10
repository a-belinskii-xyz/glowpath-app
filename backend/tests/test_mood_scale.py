"""Tests for mood score localization."""

import pytest
from app.core.mood_scale import MoodScore, mood_score_emoji, mood_score_label


@pytest.mark.parametrize(
    ("score", "locale", "expected"),
    [
        (MoodScore.GREAT, "en", "great"),
        (MoodScore.GREAT, "ru", "отлично"),
        (MoodScore.AWFUL, "ru-RU", "ужасно"),
        (MoodScore.NEUTRAL, "de", "neutral"),
    ],
)
def test_mood_score_label(score: MoodScore, locale: str, expected: str) -> None:
    assert mood_score_label(score, locale) == expected


def test_mood_score_emoji() -> None:
    assert mood_score_emoji(MoodScore.GOOD) == "🙂"
