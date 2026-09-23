import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.achievements import (
    DEFAULT_ACHIEVEMENT_ICON,
    DEFAULT_ACHIEVEMENT_ICON_TYPE,
)
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import table_name

if TYPE_CHECKING:
    from app.models.achievement_reward import AchievementReward
    from app.models.user_achievement import UserAchievement


class Achievement(TimestampMixin, Base):
    __tablename__ = table_name("achievements")
    __table_args__ = (
        CheckConstraint(
            "category IN ('getting_started', 'streaks', 'collection', 'secrets')",
            name="achievement_category_values",
        ),
        CheckConstraint(
            "visibility IN ('visible', 'secret')",
            name="achievement_visibility_values",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="achievement_status_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(32))
    visibility: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), server_default="draft")
    labels: Mapped[dict] = mapped_column(JSONB)
    descriptions: Mapped[dict] = mapped_column(JSONB)
    icon_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=DEFAULT_ACHIEVEMENT_ICON_TYPE,
    )
    icon: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=DEFAULT_ACHIEVEMENT_ICON,
    )
    criteria: Mapped[dict] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    rewards: Mapped[list["AchievementReward"]] = relationship(
        back_populates="achievement",
        cascade="all, delete-orphan",
        order_by="AchievementReward.sort_order",
    )
    user_progress: Mapped[list["UserAchievement"]] = relationship(
        back_populates="achievement",
    )
