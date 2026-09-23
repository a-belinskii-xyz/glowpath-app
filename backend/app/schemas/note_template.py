import re
import uuid
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core.markdown_plain_text import (
    NOTE_CONTENT_MAX_LENGTH,
    NOTE_RAW_MAX_LENGTH,
    markdown_content_length,
)

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


def _validate_bodies(value: dict[str, str]) -> dict[str, str]:
    if not value:
        raise ValueError("bodies must include at least one locale")
    cleaned: dict[str, str] = {}
    for locale, body in value.items():
        key = locale.strip().lower()
        text = body.strip()
        if not key:
            raise ValueError("body locale keys must be non-empty")
        if not text:
            raise ValueError("body values must be non-empty")
        if len(text) > NOTE_RAW_MAX_LENGTH:
            raise ValueError(f"Template body must be at most {NOTE_RAW_MAX_LENGTH} characters")
        if markdown_content_length(text) > NOTE_CONTENT_MAX_LENGTH:
            raise ValueError(
                f"Template body content must be at most {NOTE_CONTENT_MAX_LENGTH} characters "
                "(markdown formatting does not count)"
            )
        cleaned[key] = text
    return cleaned


Slug = Annotated[str, Field(min_length=1, max_length=64)]
Labels = Annotated[dict[str, str], Field(min_length=1)]
BodiesDict = Annotated[dict[str, str], Field(min_length=1)]


class NoteTemplatePublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    labels: dict[str, str]
    body: str
    bodies: dict[str, str]
    sort_order: int


class NoteTemplateListResponse(BaseModel):
    items: list[NoteTemplatePublic]


class NoteTemplateCreate(BaseModel):
    labels: Labels
    bodies: BodiesDict
    slug: Slug | None = None
    sort_order: int | None = None

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

    @field_validator("bodies")
    @classmethod
    def bodies_format(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_bodies(value)


class NoteTemplatePatch(BaseModel):
    slug: Slug | None = None
    labels: Labels | None = None
    bodies: BodiesDict | None = None
    sort_order: int | None = None

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

    @field_validator("bodies")
    @classmethod
    def bodies_format(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return None
        return _validate_bodies(value)


class NoteTemplateReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)
