from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.mood_scale import MoodScoreIconType


class MoodScoreStylePublic(BaseModel):
    color: str
    icon_type: MoodScoreIconType
    icon: str
    label: str


class MoodPreferencesPublic(BaseModel):
    scores: dict[str, MoodScoreStylePublic]


class MoodScoreStyleUpdate(BaseModel):
    color: str | None = None
    icon_type: MoodScoreIconType | None = None
    icon: str | None = None
    # Empty string clears a custom label and restores the locale default.
    label: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> MoodScoreStyleUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class MoodPreferencesUpdate(BaseModel):
    scores: dict[str, MoodScoreStyleUpdate] = Field(default_factory=dict)

    @model_validator(mode="after")
    def at_least_one_score(self) -> MoodPreferencesUpdate:
        if not self.scores:
            raise ValueError("At least one score style must be provided")
        return self


class BuiltinMoodIconPublic(BaseModel):
    slug: str
    label: str
    asset_path: str
    default_score: int | None = None


class MoodIconCatalogResponse(BaseModel):
    items: list[BuiltinMoodIconPublic]


class MoodIconPublic(BaseModel):
    id: UUID
    score: int
    mime_type: str
    size_bytes: int
    original_name: str
    has_source: bool = False
    preferences: MoodPreferencesPublic


class MoodIconMetaPublic(BaseModel):
    id: UUID
    score: int
    mime_type: str
    size_bytes: int
    original_name: str
    has_source: bool = False


class MoodIconListResponse(BaseModel):
    items: list[MoodIconMetaPublic]
    max_per_score: int = 3
