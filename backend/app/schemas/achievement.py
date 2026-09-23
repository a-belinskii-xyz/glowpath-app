from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AchievementRewardPublic(BaseModel):
    kind: str
    amount: int | None = None
    pack_id: UUID | None = None
    pack_slug: str | None = None
    pack_name: str | None = None
    cover_icon_id: UUID | None = None
    preview_icon_ids: list[UUID] = Field(default_factory=list)
    catalog_icon_id: UUID | None = None
    icon_slug: str | None = None
    icon_name: str | None = None


class AchievementPublic(BaseModel):
    id: UUID
    visibility: str
    category: str
    unlocked: bool
    is_new: bool = False
    progress_current: int = 0
    progress_target: int = 1
    sort_order: int = 0
    # Revealed when visible, or secret after unlock:
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    icon_type: str | None = None
    icon: str | None = None
    criteria: dict[str, Any] | None = None
    rewards: list[AchievementRewardPublic] = Field(default_factory=list)
    unlocked_at: datetime | None = None
    unlocked_by_entry_id: UUID | None = None
    unlock_percent: float | None = None


class AchievementListResponse(BaseModel):
    items: list[AchievementPublic]


class AchievementSummaryResponse(BaseModel):
    unlocked: int
    total_visible: int
    secret_unlocked: int
    secret_total: int
