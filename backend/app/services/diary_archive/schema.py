"""The current ``diary.json`` format: one place both export and restore rely on.

Changing the format means bumping ``CURRENT_VERSION``, adjusting these models and
adding one step to ``upgrades.UPGRADES`` that turns the previous version into this
one. Older archives then keep restoring through the chain of steps.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from app.core.default_tag_groups import DEFAULT_TAG_COLOR, DEFAULT_TAG_ICON
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE
from app.models.goal import DEFAULT_GOAL_COLOR, DEFAULT_GOAL_ICON
from pydantic import BaseModel, ConfigDict, Field

CURRENT_VERSION = 2

Slug = str
Labels = dict[str, str]


class _ArchiveModel(BaseModel):
    # Unknown keys are ignored so a hand-edited or slightly newer file still reads.
    model_config = ConfigDict(extra="ignore")


class ArchiveAccount(_ArchiveModel):
    email: str | None = None
    timezone: str | None = None
    created_at: datetime | None = None
    theme_preference: str | None = None
    telegram_linked: bool = False


class ArchiveTag(_ArchiveModel):
    slug: Slug = Field(min_length=1, max_length=64)
    labels: Labels
    color: str = Field(default=DEFAULT_TAG_COLOR, max_length=7)
    sort_order: int = 0
    icon_type: str = "emoji"
    icon: str = DEFAULT_TAG_ICON


class ArchiveTagGroup(_ArchiveModel):
    slug: Slug = Field(min_length=1, max_length=64)
    labels: Labels
    show_on_entry: bool = False
    sort_order: int = 0
    tags: list[ArchiveTag] = Field(default_factory=list)


class ArchiveGoalCheckin(_ArchiveModel):
    day: date
    level: Literal["partial", "full"] = "full"


class ArchiveGoal(_ArchiveModel):
    slug: Slug = Field(min_length=1, max_length=64)
    labels: Labels
    tracking_kind: Literal["binary", "quantity"] = "binary"
    times_per_week: int = Field(default=1, ge=1, le=7)
    target_amount: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=32)
    partial_label: str | None = Field(default=None, max_length=80)
    starts_on: date | None = None
    ends_on: date | None = None
    color: str = Field(default=DEFAULT_GOAL_COLOR, max_length=7)
    sort_order: int = 0
    show_on_entry: bool = False
    show_in_stats: bool = False
    icon_type: str = "emoji"
    icon: str = DEFAULT_GOAL_ICON
    # Days marked done without an entry (GP-43); older v2 archives simply have none.
    checkins: list[ArchiveGoalCheckin] = Field(default_factory=list)


class ArchiveNoteTemplate(_ArchiveModel):
    slug: Slug = Field(min_length=1, max_length=64)
    labels: Labels
    bodies: Labels
    sort_order: int = 0


class ArchiveReminder(_ArchiveModel):
    """Exported for the record; a restore never touches reminder settings."""

    kind: str
    enabled: bool = False
    time_of_day: str | None = None
    interval_days: int | None = None
    days_of_week: list[int] | None = None
    channels: list[str] = Field(default_factory=list)


class ArchiveEntryTag(_ArchiveModel):
    group: Slug
    slug: Slug
    labels: Labels = Field(default_factory=dict)
    color: str | None = Field(default=None, max_length=7)


class ArchiveEntryGoal(_ArchiveModel):
    slug: Slug
    labels: Labels = Field(default_factory=dict)
    amount: int | None = Field(default=None, ge=1)
    color: str | None = Field(default=None, max_length=7)


class ArchiveAttachment(_ArchiveModel):
    kind: Literal["photo", "audio"]
    # Path inside the ZIP part; ``None`` when the file was lost at export time.
    file: str | None = None
    part: int | None = Field(default=None, ge=1)
    mime_type: str
    size_bytes: int = Field(ge=0)
    original_name: str = ""
    position: int | None = None
    transcription: str | None = None


class ArchiveEntry(_ArchiveModel):
    id: uuid.UUID
    recorded_at: datetime
    logged_on: date | None = None
    logged_timezone: str | None = Field(default=None, max_length=64)
    score: int = Field(ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    score_color: str | None = Field(default=None, max_length=7)
    note: str | None = None
    is_favorite: bool = False
    tags: list[ArchiveEntryTag] = Field(default_factory=list)
    goals: list[ArchiveEntryGoal] = Field(default_factory=list)
    attachments: list[ArchiveAttachment] = Field(default_factory=list)


class DiaryArchive(_ArchiveModel):
    format_version: Literal[2] = 2
    exported_at: datetime
    account: ArchiveAccount = Field(default_factory=ArchiveAccount)
    tag_groups: list[ArchiveTagGroup] = Field(default_factory=list)
    goals: list[ArchiveGoal] = Field(default_factory=list)
    note_templates: list[ArchiveNoteTemplate] = Field(default_factory=list)
    reminders: list[ArchiveReminder] = Field(default_factory=list)
    entries: list[ArchiveEntry] = Field(default_factory=list)
