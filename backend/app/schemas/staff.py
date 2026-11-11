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


class StaffSignupSourcePublic(BaseModel):
    source: str
    last_7_days: int
    last_30_days: int
    total: int


class StaffWeekMetricsPublic(BaseModel):
    starts_at: datetime
    ends_at: datetime
    signups: int
    active: int
    regular: int


class StaffRetentionPublic(BaseModel):
    """Per week W1–W4 since signup; ``active``/``regular`` are null until ``eligible`` > 0."""

    size: int
    eligible: list[int]
    active: list[int | None]
    regular: list[int | None]


class StaffSourceCohortPublic(BaseModel):
    source: str
    retention: StaffRetentionPublic


class StaffWeekCohortPublic(BaseModel):
    week_start: datetime
    retention: StaffRetentionPublic
    sources: list[StaffSourceCohortPublic]


class StaffMetricsResponse(BaseModel):
    generated_at: datetime
    regular_min_days: int
    cohort_weeks: int
    sources: list[StaffSignupSourcePublic]
    weeks: list[StaffWeekMetricsPublic]
    cohorts: list[StaffWeekCohortPublic]
    cohort_total: StaffRetentionPublic
