from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.mood_scale import MoodScoreIconType

_MAX_COMPOSER_BLOCKS = 32
_MAX_COMPOSER_BLOCK_ID_LENGTH = 64


class MoodScoreStylePublic(BaseModel):
    color: str
    icon_type: MoodScoreIconType
    icon: str
    label: str


class ComposerBlockPreference(BaseModel):
    id: str = Field(min_length=1, max_length=_MAX_COMPOSER_BLOCK_ID_LENGTH)
    enabled: bool

    @field_validator("id")
    @classmethod
    def strip_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Block id must be a non-empty string")
        return cleaned


class MoodPreferencesPublic(BaseModel):
    scores: dict[str, MoodScoreStylePublic]
    use_historical_colors: bool = True
    show_streak: bool = True
    calendar_from_start: bool = False
    calendar_start_on: date | None = None
    # Local date of the first entry; the calendar start falls back to it.
    first_entry_on: date | None = None
    composer_blocks: list[ComposerBlockPreference] | None = None


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
    use_historical_colors: bool | None = None
    show_streak: bool | None = None
    calendar_from_start: bool | None = None
    # Explicit null goes back to starting from the first entry.
    calendar_start_on: date | None = None
    # Explicit null clears a saved layout so clients fall back to registry defaults.
    composer_blocks: list[ComposerBlockPreference] | None = None

    @field_validator("composer_blocks")
    @classmethod
    def limit_composer_blocks(
        cls,
        value: list[ComposerBlockPreference] | None,
    ) -> list[ComposerBlockPreference] | None:
        if value is not None and len(value) > _MAX_COMPOSER_BLOCKS:
            raise ValueError(f"At most {_MAX_COMPOSER_BLOCKS} composer blocks are allowed")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self) -> MoodPreferencesUpdate:
        if (
            not self.scores
            and self.use_historical_colors is None
            and self.show_streak is None
            and self.calendar_from_start is None
            and "calendar_start_on" not in self.model_fields_set
            and "composer_blocks" not in self.model_fields_set
        ):
            raise ValueError("At least one field must be provided")
        return self


class BuiltinMoodIconPublic(BaseModel):
    slug: str
    label: str
    asset_path: str
    suggested_score: int | None = None
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
