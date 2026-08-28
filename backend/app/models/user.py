import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.auth_token import AuthToken
    from app.models.goal import Goal
    from app.models.icon_pack import IconPack
    from app.models.icon_pack_unlock import IconPackUnlock
    from app.models.mood_entry import MoodEntry
    from app.models.note_template import NoteTemplate
    from app.models.tag_group import TagGroup
    from app.models.telegram_link_code import TelegramLinkCode
    from app.models.user_achievement import UserAchievement
    from app.models.user_catalog_icon_unlock import UserCatalogIconUnlock
    from app.models.user_goal_icon import UserGoalIcon
    from app.models.user_mood_icon import UserMoodIcon
    from app.models.user_mood_preferences import UserMoodPreferences
    from app.models.user_notification_settings import UserNotificationSettings
    from app.models.user_tag_icon import UserTagIcon
    from app.models.user_wallet import UserWallet
from app.models.user_mood_preferences import UserMoodPreferences


class User(TimestampMixin, Base):
    __tablename__ = table_name("users")
    __table_args__ = (
        CheckConstraint(
            "password_hash IS NOT NULL OR google_sub IS NOT NULL",
            name="auth_method_present",
        ),
        CheckConstraint(
            "("
            "telegram_user_id IS NULL AND telegram_chat_id IS NULL "
            "AND telegram_linked_at IS NULL"
            ") OR ("
            "telegram_user_id IS NOT NULL AND telegram_chat_id IS NOT NULL "
            "AND telegram_linked_at IS NOT NULL"
            ")",
            name="telegram_link_complete",
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
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_staff: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_locale: Mapped[str | None] = mapped_column(String(16))

    pending_guest_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("visitors"), ondelete="SET NULL"),
        nullable=True,
    )
    guest_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    mood_entries: Mapped[list["MoodEntry"]] = relationship(back_populates="user")
    tag_groups: Mapped[list["TagGroup"]] = relationship(back_populates="user")
    note_templates: Mapped[list["NoteTemplate"]] = relationship(back_populates="user")
    goals: Mapped[list["Goal"]] = relationship(back_populates="user")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user")
    telegram_link_codes: Mapped[list["TelegramLinkCode"]] = relationship(
        back_populates="user",
    )
    notification_settings: Mapped["UserNotificationSettings | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    mood_preferences: Mapped["UserMoodPreferences | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    mood_icons: Mapped[list["UserMoodIcon"]] = relationship(back_populates="user")
    goal_icons: Mapped[list["UserGoalIcon"]] = relationship(back_populates="user")
    tag_icons: Mapped[list["UserTagIcon"]] = relationship(back_populates="user")
    wallet: Mapped["UserWallet | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    authored_icon_packs: Mapped[list["IconPack"]] = relationship(
        back_populates="author",
        foreign_keys="IconPack.author_id",
    )
    icon_pack_unlocks: Mapped[list["IconPackUnlock"]] = relationship(
        back_populates="user",
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="user",
    )
    catalog_icon_unlocks: Mapped[list["UserCatalogIconUnlock"]] = relationship(
        back_populates="user",
    )

    @property
    def telegram_linked(self) -> bool:
        return self.telegram_user_id is not None and self.telegram_chat_id is not None
