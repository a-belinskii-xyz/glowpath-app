"""Time-of-day bins for companion copy. Keep in sync with frontend/backend."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYPARTS = ("lateNight", "morning", "midday", "afternoon", "evening", "night")


def companion_daypart_for_hour(hour: int) -> str:
    normalized = 0 if hour == 24 else hour
    if normalized < 5:
        return "lateNight"
    if normalized < 11:
        return "morning"
    if normalized < 14:
        return "midday"
    if normalized < 17:
        return "afternoon"
    if normalized < 21:
        return "evening"
    return "night"


def pick_companion_variant(seed: str, count: int) -> int:
    if count <= 1:
        return 0
    hash_value = 2166136261
    for char in seed:
        hash_value ^= ord(char)
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return hash_value % count


def local_now(timezone_name: str | None) -> datetime:
    try:
        tz = ZoneInfo(timezone_name) if timezone_name else ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(UTC).astimezone(tz)


def companion_key(base: str, timezone_name: str | None, *, variants: int = 3) -> str:
    instant = local_now(timezone_name)
    daypart = companion_daypart_for_hour(instant.hour)
    seed = f"{instant.date().isoformat()}:{base}:{daypart}"
    variant = pick_companion_variant(seed, variants)
    return f"{base}.{daypart}.{variant}"
