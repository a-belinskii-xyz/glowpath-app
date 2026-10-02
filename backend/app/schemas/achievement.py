from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
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


# --- Staff editor ---

AchievementCategoryValue = Literal["getting_started", "streaks", "collection", "secrets"]
AchievementVisibilityValue = Literal["visible", "secret"]
AchievementStatusValue = Literal["draft", "published", "archived"]


class AchievementTextModel(BaseModel):
    en: str = Field(min_length=1, max_length=200)
    ru: str | None = Field(default=None, max_length=200)

    def as_labels(self) -> dict[str, str]:
        en = self.en.strip()
        ru = (self.ru or "").strip()
        return {"en": en, "ru": ru or en}


class AchievementRewardInput(BaseModel):
    kind: Literal["tokens", "icon_pack", "catalog_icon"]
    amount: int | None = Field(default=None, ge=1, le=100_000)
    pack_id: UUID | None = None
    catalog_icon_id: UUID | None = None


class StaffAchievementCreate(BaseModel):
    labels: AchievementTextModel
    descriptions: AchievementTextModel
    category: AchievementCategoryValue = "collection"
    visibility: AchievementVisibilityValue = "visible"
    criteria: dict[str, Any]
    rewards: list[AchievementRewardInput] = Field(default_factory=list, max_length=10)
    emoji: str | None = Field(default=None, max_length=16)
    slug: str | None = Field(default=None, max_length=64)
    sort_order: int | None = None


class StaffAchievementPatch(BaseModel):
    labels: AchievementTextModel | None = None
    descriptions: AchievementTextModel | None = None
    category: AchievementCategoryValue | None = None
    visibility: AchievementVisibilityValue | None = None
    status: AchievementStatusValue | None = None
    criteria: dict[str, Any] | None = None
    rewards: list[AchievementRewardInput] | None = Field(default=None, max_length=10)
    emoji: str | None = Field(default=None, max_length=16)
    sort_order: int | None = None


class StaffAchievementRewardPublic(BaseModel):
    kind: str
    amount: int | None = None
    pack_id: UUID | None = None
    catalog_icon_id: UUID | None = None
    # Pack of a single-icon reward, so the editor can list that pack's icons.
    icon_pack_id: UUID | None = None
    label: str | None = None


class StaffAchievementPublic(BaseModel):
    id: UUID
    slug: str
    category: str
    visibility: str
    status: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    name: str
    icon_type: str
    icon: str
    criteria: dict[str, Any]
    sort_order: int
    rewards: list[StaffAchievementRewardPublic] = Field(default_factory=list)
    unlocked_count: int = 0
    updated_at: datetime


class StaffAchievementListResponse(BaseModel):
    items: list[StaffAchievementPublic]


class CriteriaParamSpecPublic(BaseModel):
    name: str
    kind: str
    required: bool
    minimum: int | None = None
    maximum: int | None = None
    choices: list[str | int] = Field(default_factory=list)
    default: int | str | None = None


class CriteriaSpecPublic(BaseModel):
    type: str
    require_any_of: list[str] = Field(default_factory=list)
    params: list[CriteriaParamSpecPublic]


class CriteriaSpecListResponse(BaseModel):
    items: list[CriteriaSpecPublic]
