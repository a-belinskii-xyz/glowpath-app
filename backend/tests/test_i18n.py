"""Tests for locale resolution helpers."""

import pytest
from app.core.i18n import (
    parse_accept_language,
    resolve_label,
)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("ru", "ru"),
        ("ru-RU,ru;q=0.9,en-US;q=0.8", "ru"),
        ("de-DE,de;q=0.9", "en"),
        ("en-US,en;q=0.9,ru;q=0.8", "en"),
    ],
)
def test_parse_accept_language(header: str | None, expected: str) -> None:
    assert parse_accept_language(header) == expected


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("ru", "Погода"),
        ("ru-RU", "Погода"),
        ("en", "Weather"),
        ("de", "Weather"),
    ],
)
def test_resolve_label(locale: str, expected: str) -> None:
    labels = {"en": "Weather", "ru": "Погода"}
    assert resolve_label(labels, locale) == expected


def test_resolve_label_falls_back_to_any_available() -> None:
    assert resolve_label({"ru": "Погода"}, "en") == "Погода"
