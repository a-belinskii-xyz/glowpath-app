import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    timezone: str
    email_verified: bool
    email_verified_at: datetime | None

    model_config = {"from_attributes": True}
