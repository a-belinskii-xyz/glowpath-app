from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.mood_entry_source import MoodEntrySource
from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE
from app.schemas.mood_entry import NoteField


class TelegramLinkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    linked: bool
    telegram_user_id: int | None = None
    telegram_linked_at: datetime | None = None
    bot_username: str | None = None
    bot_configured: bool = False
    can_unlink: bool = False


class TelegramEntryPointPublic(BaseModel):
    bot_username: str | None = None
    bot_url: str | None = None


class TelegramLinkCodeCreateResponse(BaseModel):
    code: str
    expires_at: datetime
    deep_link: str


class TelegramBotLinkRequest(BaseModel):
    code: str = Field(min_length=8, max_length=64)
    telegram_user_id: int = Field(gt=0)
    telegram_chat_id: int
    locale: str | None = Field(default=None, max_length=16)


class TelegramBotUnlinkRequest(BaseModel):
    telegram_user_id: int = Field(gt=0)


class TelegramBotMePublic(BaseModel):
    linked: bool
    user_id: str | None = None
    email: str | None = None
    timezone: str | None = None
    locale: str | None = None
    onboarding_completed: bool = False


class TelegramBotCatalogScore(BaseModel):
    score: int
    label: str
    emoji: str
    color: str
    icon_type: str
    icon: str


class TelegramBotCatalogTag(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    sort_order: int = 0


class TelegramBotCatalogTagGroup(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    sort_order: int = 0
    show_on_entry: bool = True
    tags: list[TelegramBotCatalogTag]


class TelegramBotCatalogGoal(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    color: str
    icon_type: str
    icon: str
    show_on_entry: bool = True


class TelegramBotCatalogPublic(BaseModel):
    locale: str
    timezone: str
    scores: list[TelegramBotCatalogScore]
    tag_groups: list[TelegramBotCatalogTagGroup]
    frequent_tags: list[TelegramBotCatalogTag] = Field(default_factory=list)
    goals: list[TelegramBotCatalogGoal]


class TelegramBotEntryCreate(BaseModel):
    telegram_user_id: int = Field(gt=0)
    score: int = Field(ge=MIN_MOOD_SCORE, le=MAX_MOOD_SCORE)
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    goal_ids: list[uuid.UUID] = Field(default_factory=list)
    note: NoteField = None
    source: MoodEntrySource | None = None


class TelegramBotSessionPublic(BaseModel):
    telegram_user_id: int
    state: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None


class TelegramBotSessionUpsert(BaseModel):
    state: dict[str, Any] = Field(default_factory=dict)
