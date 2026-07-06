"""Shared i18n helpers for localized labels (ru, en)."""

from typing import Final

SUPPORTED_LOCALES: Final[frozenset[str]] = frozenset({"en", "ru"})
DEFAULT_LOCALE: Final[str] = "en"

type LocaleLabels = dict[str, str]


def normalize_locale(locale: str) -> str:
    """Map a locale tag to a supported language code, e.g. ``ru-RU`` → ``ru``."""
    primary = locale.split(",")[0].split(";")[0].strip().lower()
    if "-" in primary:
        primary = primary.split("-")[0]
    if primary in SUPPORTED_LOCALES:
        return primary
    return DEFAULT_LOCALE


def parse_accept_language(header: str | None) -> str:
    """Pick the best supported locale from an ``Accept-Language`` header."""
    if not header:
        return DEFAULT_LOCALE
    for part in header.split(","):
        lang = part.split(";")[0].strip().lower()
        if "-" in lang:
            lang = lang.split("-")[0]
        if lang in SUPPORTED_LOCALES:
            return lang
    return DEFAULT_LOCALE


def resolve_label(labels: LocaleLabels, locale: str) -> str:
    """Return a label for *locale* with fallback to ``en``, then any available value."""
    normalized = normalize_locale(locale)
    if normalized in labels:
        return labels[normalized]
    if DEFAULT_LOCALE in labels:
        return labels[DEFAULT_LOCALE]
    return next(iter(labels.values()))
