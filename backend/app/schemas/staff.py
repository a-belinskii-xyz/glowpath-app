from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.marketplace import PackLabelsModel


class StaffUserPublic(BaseModel):
    id: UUID
    email: str | None = None
    telegram_linked: bool = False
    is_staff: bool = False
    balance: int = 0
    created_at: datetime


class StaffUserListResponse(BaseModel):
    items: list[StaffUserPublic]


class StaffPackCreate(BaseModel):
    labels: PackLabelsModel
    slug: str | None = Field(default=None, max_length=64)
    price_tokens: int = Field(default=0, ge=0)
    sort_order: int = 0


class StaffPackSortBody(BaseModel):
    sort_order: int


class PresetImportResponse(BaseModel):
    search_tags: int
    packs: list[str]
    icons: int
    achievements: list[str]
