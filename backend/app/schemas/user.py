import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, EmailStr, Field, model_validator

ThemePreference = Literal["system", "light", "dark"]
UserLocale = Literal["en", "ru"]


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr | None = None
    timezone: str
    email_verified: bool
    email_verified_at: datetime | None
    onboarding_completed: bool
    onboarding_completed_at: datetime | None
    has_password: bool
    is_staff: bool = False
    theme_preference: ThemePreference = "system"
    locale: UserLocale | None = None
    telegram_linked: bool = False
    can_unlink_telegram: bool = False
    features: dict[str, bool] = Field(default_factory=dict)
    plan: str = "free"
    entitlements: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    theme_preference: ThemePreference | None = None
    locale: UserLocale | None = None

    @model_validator(mode="after")
    def _require_any_field(self) -> Self:
        if self.timezone is None and self.theme_preference is None and self.locale is None:
            raise ValueError("At least one field must be provided")
        return self
