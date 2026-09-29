from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.notifications.base import NotificationChannel


class NotificationScheduleKind(StrEnum):
    DAILY_MOOD = "daily_mood"
    GOAL_TRACKING = "goal_tracking"
    WEEKLY_DIGEST = "weekly_digest"
    CUSTOM_REMINDER = "custom_reminder"


class WorkerLiveness(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class NotificationStatusCode(StrEnum):
    OK = "OK"
    DISABLED_STAGE_TESTING = "DISABLED_STAGE_TESTING"
    WORKER_OFFLINE = "WORKER_OFFLINE"


PROVISIONED_KINDS: tuple[NotificationScheduleKind, ...] = (
    NotificationScheduleKind.DAILY_MOOD,
    NotificationScheduleKind.GOAL_TRACKING,
)

DEFAULT_TIME_BY_KIND: dict[NotificationScheduleKind, str] = {
    NotificationScheduleKind.DAILY_MOOD: "21:00",
    NotificationScheduleKind.GOAL_TRACKING: "12:00",
    NotificationScheduleKind.WEEKLY_DIGEST: "09:00",
    NotificationScheduleKind.CUSTOM_REMINDER: "18:00",
}


class NotificationSystemStatus(BaseModel):
    feature_enabled: bool
    worker_status: WorkerLiveness
    status_code: NotificationStatusCode
    message: str


class NotificationSchedulePublic(BaseModel):
    kind: NotificationScheduleKind
    enabled: bool
    time_of_day: str
    interval_days: int
    days_of_week: list[int] | None = None
    channels: list[NotificationChannel]
    last_sent_at: datetime | None = None


class NotificationSettingsPublic(BaseModel):
    system_status: NotificationSystemStatus
    schedules: list[NotificationSchedulePublic]


class NotificationScheduleUpdate(BaseModel):
    enabled: bool | None = None
    time_of_day: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=30)
    days_of_week: list[int] | None = None
    channels: list[NotificationChannel] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def at_least_one_field(self) -> NotificationScheduleUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self

    @field_validator("time_of_day")
    @classmethod
    def valid_clock(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_time_of_day(value)

    @field_validator("days_of_week")
    @classmethod
    def valid_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        unique = sorted(set(value))
        if any(day < 0 or day > 6 for day in unique):
            raise ValueError("days_of_week values must be between 0 and 6")
        return unique


def normalize_time_of_day(value: str) -> str:
    raw = value.strip()
    parts = raw.split(":")
    if len(parts) < 2:
        raise ValueError("time_of_day must be HH:MM")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError("time_of_day must be HH:MM") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("time_of_day must be HH:MM")
    return f"{hour:02d}:{minute:02d}"


class ReminderTickResponse(BaseModel):
    outcome: str
    users_considered: int
    daily_mood_sent: int
    goal_reminders_sent: int
    skipped: int
    errors: int
