import pytest
from app.core.emoji import is_single_emoji


@pytest.mark.parametrize(
    "value",
    [
        "🙂",
        "🫠",
        "❤️",
        "☀",
        "👍🏽",
        "👩🏽‍💻",
        "👨‍👩‍👧",
        "🇷🇺",
        "1️⃣",
        "#⃣",
        "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    ],
)
def test_is_single_emoji_accepts_emoji(value: str) -> None:
    assert is_single_emoji(value)


@pytest.mark.parametrize(
    "value",
    ["", "a", "ok", "1", "#", "→", "😀😀", "🙂 ok", "ok🙂", "🇷", "‍🙂", "🙂‍"],
)
def test_is_single_emoji_rejects_text(value: str) -> None:
    assert not is_single_emoji(value)
