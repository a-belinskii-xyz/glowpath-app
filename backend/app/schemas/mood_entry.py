import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.core.attachment_kind import AttachmentKind
from app.core.goal_tracking import MAX_GOAL_AMOUNT, GoalTrackingKind
from app.core.markdown_plain_text import (
    NOTE_CONTENT_MAX_LENGTH,
    NOTE_RAW_MAX_LENGTH,
    markdown_content_length,
)
from app.core.mood_entry_source import MoodEntrySource
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE, MoodScoreIconType


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


class MoodEntryGoalProgress(BaseModel):
    goal_id: uuid.UUID
    amount: int = Field(ge=1, le=MAX_GOAL_AMOUNT)


class MoodEntryCreate(BaseModel):
    score: int = Field(ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime
    note: NoteField = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    goal_ids: list[uuid.UUID] = Field(default_factory=list)
    goal_progress: list[MoodEntryGoalProgress] = Field(default_factory=list)
    # Analytics attribution from notification deep links; not returned in public responses.
    source: MoodEntrySource | None = None


class MoodEntryPatch(BaseModel):
    score: int | None = Field(default=None, ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime | None = None
    note: NoteField = None
    tag_ids: list[uuid.UUID] | None = None
    goal_ids: list[uuid.UUID] | None = None
    goal_progress: list[MoodEntryGoalProgress] | None = None
    is_favorite: bool | None = None


class MoodEntryTagPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    group_id: uuid.UUID
    color: str
    icon_type: str
    icon: str


class MoodEntryGoalPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    color: str
    icon_type: str
    icon: str
    tracking_kind: GoalTrackingKind = GoalTrackingKind.BINARY
    target_amount: int | None = None
    unit: str | None = None
    amount: int | None = None


class AttachmentPublic(BaseModel):
    id: uuid.UUID
    kind: AttachmentKind
    mime_type: str
    size_bytes: int
    original_name: str
    position: int | None
    transcription: str | None = None


class AttachmentReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class MoodEntryPublic(BaseModel):
    id: uuid.UUID
    recorded_at: datetime
    score: int
    score_label: str
    score_emoji: str
    score_color: str
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
    score_color: str


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


class MoodRecapItemPublic(BaseModel):
    id: uuid.UUID
    kind: str
    label: str
    color: str
    icon_type: MoodScoreIconType
    icon: str
    count: int


class MoodEntryStatsResponse(BaseModel):
    total_entries: int
    scores: list[MoodScoreStatPublic]
    month_index: float | None
    active_days: int
    comparison: MoodMonthComparisonPublic
    favorite_count: int = 0
    tags: list[MoodRecapItemPublic] = Field(default_factory=list)
    goals: list[MoodRecapItemPublic] = Field(default_factory=list)


class InsightStatsPublic(BaseModel):
    delta: float | None
    lift: float | None
    group_mean: float | None
    complement_mean: float | None
    group_share: float | None
    complement_share: float | None
    group_n: int
    complement_n: int


class InsightSubjectPublic(BaseModel):
    type: str
    key: str
    label: str
    id: uuid.UUID | None = None
    slug: str | None = None
    color: str | None = None
    icon_type: str | None = None
    icon: str | None = None


class MoodInsightPublic(BaseModel):
    id: str
    kind: str
    direction: str
    strength: str
    title: str
    body: str
    sample: str
    stats: InsightStatsPublic
    subjects: list[InsightSubjectPublic]


class MoodInsightsResponse(BaseModel):
    window_from: datetime
    window_to: datetime
    active_days: int
    entry_count: int
    baseline_index: float | None
    items: list[MoodInsightPublic]
