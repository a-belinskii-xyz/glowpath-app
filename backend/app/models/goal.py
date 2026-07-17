import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.mood_entry_goal import MoodEntryGoal
    from app.models.user import User
    from app.models.user_goal_icon import UserGoalIcon

DEFAULT_GOAL_COLOR = "#60a5fa"
DEFAULT_GOAL_ICON_TYPE = "emoji"
DEFAULT_GOAL_ICON = "🎯"


class Goal(TimestampMixin, Base):
    __tablename__ = table_name("goals")
    __table_args__ = (
        UniqueConstraint("user_id", "slug"),
        CheckConstraint("times_per_week >= 1 AND times_per_week <= 7", name="times_per_week_range"),
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
    slug: Mapped[str] = mapped_column(String(64))
    labels: Mapped[dict[str, str]] = mapped_column(JSONB)
    times_per_week: Mapped[int] = mapped_column(Integer)
    starts_on: Mapped[date] = mapped_column(Date)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    show_on_entry: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        server_default=DEFAULT_GOAL_COLOR,
    )
    icon_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=DEFAULT_GOAL_ICON_TYPE,
    )
    icon: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=DEFAULT_GOAL_ICON,
    )

    user: Mapped["User"] = relationship(back_populates="goals")
    entry_links: Mapped[list["MoodEntryGoal"]] = relationship(back_populates="goal")
    icons: Mapped[list["UserGoalIcon"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
    )
