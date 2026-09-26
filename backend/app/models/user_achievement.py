import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name, unique_index_name

if TYPE_CHECKING:
    from app.models.achievement import Achievement
    from app.models.mood_entry import MoodEntry
    from app.models.user import User


class UserAchievement(TimestampMixin, Base):
    __tablename__ = table_name("user_achievements")
    __table_args__ = (
        CheckConstraint(
            "progress_current >= 0",
            name="user_achievement_progress_current_non_negative",
        ),
        CheckConstraint(
            "progress_target >= 1",
            name="user_achievement_progress_target_positive",
        ),
        UniqueConstraint(
            "user_id",
            "achievement_id",
            name=unique_index_name("user_achievements", "user_achievement"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        index=True,
    )
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("achievements"), ondelete="CASCADE"),
        index=True,
    )
    progress_current: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    progress_target: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    unlocked_by_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("mood_entries"), ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rewards_snapshot: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(back_populates="user_progress")
    unlocked_by_entry: Mapped["MoodEntry | None"] = relationship(
        foreign_keys=[unlocked_by_entry_id],
    )
