import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr | None = None
    timezone: str
    email_verified: bool
    email_verified_at: datetime | None
    onboarding_completed: bool
    onboarding_completed_at: datetime | None
    has_password: bool
    telegram_linked: bool = False
    can_unlink_telegram: bool = False
    features: dict[str, bool] = Field(default_factory=dict)
    plan: str = "free"
    entitlements: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
