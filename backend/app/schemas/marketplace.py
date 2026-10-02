from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PackLabelsModel(BaseModel):
    name: dict[str, str]
    description: dict[str, str] | None = None


class SearchTagPublic(BaseModel):
    id: UUID
    slug: str
    label: str
    labels: dict[str, str]
    sort_order: int = 0
    is_active: bool = True


class SearchTagListResponse(BaseModel):
    items: list[SearchTagPublic]


class SearchTagCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    labels: dict[str, str]
    sort_order: int = 0
    is_active: bool = True


class SearchTagPatch(BaseModel):
    labels: dict[str, str] | None = None
    sort_order: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> SearchTagPatch:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class IconCropModel(BaseModel):
    """Visible square of the icon, as fractions of the image width and height."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class CatalogIconPublic(BaseModel):
    id: UUID
    pack_id: UUID
    slug: str
    label: str
    labels: dict[str, str]
    mime_type: str
    size_bytes: int
    suggested_colors: list[str]
    suggested_mood_scores: list[int]
    suggested_usage: list[str] = Field(default_factory=list)
    crop: IconCropModel | None = None
    sort_order: int
    search_tags: list[SearchTagPublic] = Field(default_factory=list)


class PackCardPublic(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    labels: dict[str, dict[str, str]]
    is_official: bool
    status: str
    price_tokens: int
    unlocked: bool
    icon_count: int
    cover_icon_id: UUID | None = None
    search_tags: list[str] = Field(default_factory=list)
    sort_order: int = 0
    published_at: datetime | None = None
    author_id: UUID | None = None
    moderation_note: str | None = None


class PackDetailPublic(PackCardPublic):
    icons: list[CatalogIconPublic] = Field(default_factory=list)


class PackListResponse(BaseModel):
    items: list[PackCardPublic]


class CatalogIconWithPackPublic(CatalogIconPublic):
    pack: PackCardPublic


class IconListResponse(BaseModel):
    items: list[CatalogIconWithPackPublic]


class PackUnlockPublic(BaseModel):
    pack_id: UUID
    unlocked_at: datetime
    pack: PackCardPublic | None = None


class PackUnlockListResponse(BaseModel):
    items: list[PackUnlockPublic]


class StudioPackCreate(BaseModel):
    labels: PackLabelsModel
    slug: str | None = Field(default=None, max_length=64)
    price_tokens: int = Field(default=0, ge=0)


class StudioPackPatch(BaseModel):
    labels: PackLabelsModel | None = None
    price_tokens: int | None = Field(default=None, ge=0)
    cover_icon_id: UUID | None = None
    clear_cover: bool = False

    @model_validator(mode="after")
    def at_least_one_field(self) -> StudioPackPatch:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class StudioIconPatch(BaseModel):
    labels: dict[str, str] | None = None
    suggested_colors: list[str] | None = None
    suggested_mood_scores: list[int] | None = None
    suggested_usage: list[str] | None = None
    search_tag_slugs: list[str] | None = None
    sort_order: int | None = None
    crop: IconCropModel | None = None
    clear_crop: bool = False

    @model_validator(mode="after")
    def at_least_one_field(self) -> StudioIconPatch:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class IconOrderBody(BaseModel):
    icon_ids: list[UUID]


class RejectPackBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class WalletPublic(BaseModel):
    balance: int


class WalletLedgerEntryPublic(BaseModel):
    id: UUID
    delta: int
    balance_after: int
    kind: str
    pack_id: UUID | None = None
    note: str | None = None
    created_at: datetime


class WalletLedgerListResponse(BaseModel):
    items: list[WalletLedgerEntryPublic]


class WalletGrantBody(BaseModel):
    user_id: UUID
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)
