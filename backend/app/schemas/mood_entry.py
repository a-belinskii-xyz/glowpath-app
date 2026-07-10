import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.attachment_kind import AttachmentKind
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE


class MoodEntryCreate(BaseModel):
    score: int = Field(ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime
    note: str | None = Field(default=None, max_length=500)
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


class MoodEntryPatch(BaseModel):
    score: int | None = Field(default=None, ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    recorded_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)
    tag_ids: list[uuid.UUID] | None = None


class MoodEntryTagPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    group_id: uuid.UUID


class AttachmentPublic(BaseModel):
    id: uuid.UUID
    kind: AttachmentKind
    mime_type: str
    size_bytes: int
    original_name: str
    position: int | None


class MoodEntryPublic(BaseModel):
    id: uuid.UUID
    recorded_at: datetime
    score: int
    score_label: str
    score_emoji: str
    note: str | None
    tags: list[MoodEntryTagPublic]
    attachments: list[AttachmentPublic]
    created_at: datetime
    updated_at: datetime


class MoodEntryListResponse(BaseModel):
    items: list[MoodEntryPublic]
    limit: int
    offset: int
