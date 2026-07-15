from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator


class MoodEntryAttributionKind(StrEnum):
    """What notification prompted the entry (analytics only)."""

    DAILY_MOOD_REMINDER = "daily_mood_reminder"
    GOAL_REMINDER = "goal_reminder"


# Keep in sync with ``NotificationChannel`` values.
_SOURCE_CHANNELS = frozenset({"email", "telegram"})


def format_mood_entry_source(*, channel: str, kind: MoodEntryAttributionKind | str) -> str:
    """Build ``{channel}:{kind}`` attribution, e.g. ``email:daily_mood_reminder``."""
    channel_value = channel.strip().lower()
    kind_value = kind.value if isinstance(kind, MoodEntryAttributionKind) else str(kind)
    if channel_value not in _SOURCE_CHANNELS:
        raise ValueError(f"Unknown notification channel for attribution: {channel!r}")
    MoodEntryAttributionKind(kind_value)  # validate
    return f"{channel_value}:{kind_value}"


def parse_mood_entry_source(raw: str) -> tuple[str, MoodEntryAttributionKind]:
    channel, sep, kind = raw.partition(":")
    if not sep or not channel or not kind or ":" in kind:
        raise ValueError(
            "source must be '{channel}:{kind}', "
            f"e.g. 'email:{MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value}'"
        )
    channel_value = channel.strip().lower()
    if channel_value not in _SOURCE_CHANNELS:
        raise ValueError(f"Unknown notification channel for attribution: {channel!r}")
    return channel_value, MoodEntryAttributionKind(kind)


def _validate_mood_entry_source(value: str) -> str:
    channel, kind = parse_mood_entry_source(value)
    return format_mood_entry_source(channel=channel, kind=kind)


MoodEntrySource = Annotated[str, AfterValidator(_validate_mood_entry_source)]
