import re
import uuid
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core.mood_scale import MoodScoreIconType

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _validate_slug(value: str) -> str:
    if not _SLUG_RE.fullmatch(value):
        raise ValueError(
            "slug must be 1–64 chars, start with a letter, and contain only a-z, 0-9, underscore"
        )
    return value


def _validate_labels(value: dict[str, str]) -> dict[str, str]:
    if not value:
        raise ValueError("labels must include at least one locale")
    cleaned: dict[str, str] = {}
    for locale, label in value.items():
        key = locale.strip().lower()
        text = label.strip()
        if not key:
            raise ValueError("label locale keys must be non-empty")
        if not text:
            raise ValueError("label values must be non-empty")
        cleaned[key] = text
    return cleaned


Slug = Annotated[str, Field(min_length=1, max_length=64)]
Labels = Annotated[dict[str, str], Field(min_length=1)]
Color = Annotated[str, Field(min_length=7, max_length=7)]
IconValue = Annotated[str, Field(min_length=1, max_length=64)]


class TagPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    labels: dict[str, str]
    group_id: uuid.UUID
    sort_order: int
    color: str
    icon_type: MoodScoreIconType
    icon: str


class TagGroupPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    labels: dict[str, str]
    sort_order: int
    show_on_entry: bool
    tags: list[TagPublic]


class TagGroupListResponse(BaseModel):
    items: list[TagGroupPublic]
    entry_visible_tag_group_limit: int


class TagGroupCreate(BaseModel):
    labels: Labels
    slug: Slug | None = None
    sort_order: int | None = None
    show_on_entry: bool = False

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_slug(value)

    @field_validator("labels")
    @classmethod
    def labels_format(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_labels(value)


class TagGroupPatch(BaseModel):
    slug: Slug | None = None
    labels: Labels | None = None
    sort_order: int | None = None
    show_on_entry: bool | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_slug(value)

    @field_validator("labels")
    @classmethod
    def labels_format(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        return _validate_labels(value)


class TagCreate(BaseModel):
    labels: Labels
    slug: Slug | None = None
    sort_order: int | None = None
    color: Color | None = None
    icon_type: MoodScoreIconType | None = None
    icon: IconValue | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_slug(value)

    @field_validator("labels")
    @classmethod
    def labels_format(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_labels(value)


class TagPatch(BaseModel):
    slug: Slug | None = None
    labels: Labels | None = None
    sort_order: int | None = None
    color: Color | None = None
    icon_type: MoodScoreIconType | None = None
    icon: IconValue | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_slug(value)

    @field_validator("labels")
    @classmethod
    def labels_format(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        return _validate_labels(value)


class TagReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class TagGroupReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class TagIconMetaPublic(BaseModel):
    id: uuid.UUID
    tag_id: uuid.UUID
    mime_type: str
    size_bytes: int
    original_name: str
    has_source: bool = False


class TagIconPublic(BaseModel):
    id: uuid.UUID
    tag_id: uuid.UUID
    mime_type: str
    size_bytes: int
    original_name: str
    has_source: bool = False
    tag: TagPublic


class TagIconListResponse(BaseModel):
    items: list[TagIconMetaPublic]
    max_per_tag: int = 3
