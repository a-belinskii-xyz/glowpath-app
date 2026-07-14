from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoggingStyle:
    """How often and how densely this persona logs mood entries."""

    label: str
    # Base probability of at least one entry on a given calendar day.
    day_chance: float
    # Added on Saturday/Sunday (can be negative).
    weekend_delta: float = 0.0
    # Momentum: adjust chance based on whether yesterday had an entry.
    streak_bonus: float = 0.0
    gap_bonus: float = 0.0
    # Dense vs sparse days when they do log.
    entries_min: int = 1
    entries_max: int = 2
    # Per-entry content tendencies.
    note_skip_chance: float = 0.15
    photo_chance: float = 0.20
    audio_chance: float = 0.08
    # Scale day_chance on odd/even ISO weeks (for on/off week personas).
    odd_week_factor: float = 1.0
    even_week_factor: float = 1.0


# Named presets used by personas — keeps PERSONAS readable.
CONSISTENT = LoggingStyle(
    label="consistent",
    day_chance=0.52,
    weekend_delta=0.12,
    streak_bonus=0.10,
    gap_bonus=-0.04,
    entries_min=1,
    entries_max=2,
    note_skip_chance=0.12,
    photo_chance=0.28,
    audio_chance=0.06,
)

SPARSE = LoggingStyle(
    label="sparse",
    day_chance=0.16,
    weekend_delta=0.04,
    streak_bonus=-0.03,
    gap_bonus=0.02,
    entries_min=1,
    entries_max=1,
    note_skip_chance=0.25,
    photo_chance=0.10,
    audio_chance=0.04,
)

WEEKDAY_WORKER = LoggingStyle(
    label="weekday",
    day_chance=0.40,
    weekend_delta=-0.28,
    streak_bonus=0.08,
    gap_bonus=-0.02,
    entries_min=1,
    entries_max=3,
    note_skip_chance=0.20,
    photo_chance=0.12,
    audio_chance=0.05,
)

SOCIAL_BURSTS = LoggingStyle(
    label="bursts",
    day_chance=0.20,
    weekend_delta=0.22,
    streak_bonus=0.22,
    gap_bonus=-0.06,
    entries_min=1,
    entries_max=3,
    note_skip_chance=0.10,
    photo_chance=0.40,
    audio_chance=0.08,
)

REFLECTIVE = LoggingStyle(
    label="reflective",
    day_chance=0.11,
    weekend_delta=0.08,
    streak_bonus=0.05,
    gap_bonus=0.0,
    entries_min=1,
    entries_max=1,
    note_skip_chance=0.05,
    photo_chance=0.15,
    audio_chance=0.22,
)

IRREGULAR = LoggingStyle(
    label="irregular",
    day_chance=0.26,
    weekend_delta=0.10,
    streak_bonus=-0.05,
    gap_bonus=0.04,
    entries_min=1,
    entries_max=2,
    note_skip_chance=0.18,
    photo_chance=0.25,
    audio_chance=0.07,
)

ON_OFF_WEEKS = LoggingStyle(
    label="on-off weeks",
    day_chance=0.28,
    weekend_delta=-0.05,
    streak_bonus=0.12,
    gap_bonus=-0.04,
    entries_min=1,
    entries_max=3,
    note_skip_chance=0.22,
    photo_chance=0.14,
    audio_chance=0.05,
    odd_week_factor=1.7,
    even_week_factor=0.35,
)

WEEKEND_NATURE = LoggingStyle(
    label="weekends",
    day_chance=0.07,
    weekend_delta=0.40,
    streak_bonus=0.06,
    gap_bonus=0.0,
    entries_min=1,
    entries_max=2,
    note_skip_chance=0.08,
    photo_chance=0.45,
    audio_chance=0.10,
)
