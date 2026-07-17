import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.core.attachment_kind import AttachmentKind
from app.core.markdown_plain_text import (
    NOTE_CONTENT_MAX_LENGTH,
    NOTE_RAW_MAX_LENGTH,
    markdown_content_length,
)
from app.core.mood_entry_source import MoodEntrySource
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE


def _validate_note(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > NOTE_RAW_MAX_LENGTH:
        raise ValueError(f"Note must be at most {NOTE_RAW_MAX_LENGTH} characters")
    if markdown_content_length(value) > NOTE_CONTENT_MAX_LENGTH:
        raise ValueError(
            f"Note content must be at most {NOTE_CONTENT_MAX_LENGTH} characters "
            "(markdown formatting does not count)"
        )
    return value


NoteField = Annotated[str | None, AfterValidator(_validate_note)]


class MoodEntryCreate(BaseModel):
    score: int = Field(ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime
    note: NoteField = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    goal_ids: list[uuid.UUID] = Field(default_factory=list)
    # Analytics attribution from notification deep links; not returned in public responses.
    source: MoodEntrySource | None = None


class MoodEntryPatch(BaseModel):
    score: int | None = Field(default=None, ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime | None = None
    note: NoteField = None
    tag_ids: list[uuid.UUID] | None = None
    goal_ids: list[uuid.UUID] | None = None
    is_favorite: bool | None = None


class MoodEntryTagPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    group_id: uuid.UUID


class MoodEntryGoalPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    color: str
    icon_type: str
    icon: str


class AttachmentPublic(BaseModel):
    id: uuid.UUID
    kind: AttachmentKind
    mime_type: str
    size_bytes: int
    original_name: str
    position: int | None
    transcription: str | None = None


class MoodEntryPublic(BaseModel):
    id: uuid.UUID
    recorded_at: datetime
    score: int
    score_label: str
    score_emoji: str
    note: str | None
    is_favorite: bool
    tags: list[MoodEntryTagPublic]
    goals: list[MoodEntryGoalPublic]
    attachments: list[AttachmentPublic]
    created_at: datetime
    updated_at: datetime


class MoodEntryListResponse(BaseModel):
    items: list[MoodEntryPublic]
    limit: int
    offset: int


class CalendarDayScore(BaseModel):
    score: int
    score_emoji: str


class CalendarDayPublic(BaseModel):
    date: str
    entry_count: int
    scores: list[CalendarDayScore]


class MoodEntryCalendarResponse(BaseModel):
    days: list[CalendarDayPublic]


class MoodScoreStatPublic(BaseModel):
    score: int
    score_label: str
    score_emoji: str
    count: int


class MoodMonthComparisonPublic(BaseModel):
    verdict: str
    message: str
    current_index: float | None
    previous_index: float | None
    delta: float | None
    current_active_days: int
    previous_active_days: int


class MoodEntryStatsResponse(BaseModel):
    total_entries: int
    scores: list[MoodScoreStatPublic]
    month_index: float | None
    active_days: int
    comparison: MoodMonthComparisonPublic
