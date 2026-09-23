from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.services.notifications.base import NotificationChannel


class NotificationSettingsPublic(BaseModel):
    enabled: bool
    channels: list[NotificationChannel]
    daily_mood_reminder_enabled: bool
    daily_mood_reminder_time: time | None
    goal_reminders_enabled: bool


class NotificationSettingsUpdate(BaseModel):
    enabled: bool | None = None
    channels: list[NotificationChannel] | None = Field(default=None, min_length=1)
    daily_mood_reminder_enabled: bool | None = None
    daily_mood_reminder_time: time | None = None
    goal_reminders_enabled: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> NotificationSettingsUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
