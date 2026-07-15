import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import table_name

if TYPE_CHECKING:
    from app.models.auth_token import AuthToken
    from app.models.goal import Goal
    from app.models.mood_entry import MoodEntry
    from app.models.note_template import NoteTemplate
    from app.models.tag_group import TagGroup
    from app.models.user_notification_settings import UserNotificationSettings


class User(TimestampMixin, Base):
    __tablename__ = table_name("users")
    __table_args__ = (
        CheckConstraint(
            "password_hash IS NOT NULL OR google_sub IS NOT NULL",
            name="auth_method_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), server_default="Europe/Minsk")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    mood_entries: Mapped[list["MoodEntry"]] = relationship(back_populates="user")
    tag_groups: Mapped[list["TagGroup"]] = relationship(back_populates="user")
    note_templates: Mapped[list["NoteTemplate"]] = relationship(back_populates="user")
    goals: Mapped[list["Goal"]] = relationship(back_populates="user")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user")
    notification_settings: Mapped["UserNotificationSettings | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
