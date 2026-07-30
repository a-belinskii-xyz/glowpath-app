import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    timezone: str
    email_verified: bool
    email_verified_at: datetime | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
