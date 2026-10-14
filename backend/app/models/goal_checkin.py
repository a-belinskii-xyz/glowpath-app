import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.goal import Goal


class GoalCheckin(TimestampMixin, Base):
    """A goal marked done on a local day without writing a mood entry (GP-43)."""

    __tablename__ = table_name("goal_checkins")
    __table_args__ = (
        UniqueConstraint("goal_id", "day"),
        CheckConstraint("level IN ('partial', 'full')", name="goal_checkin_level_values"),
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
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("goals"), ondelete="CASCADE"),
    )
    day: Mapped[date] = mapped_column(Date)
    level: Mapped[str] = mapped_column(String(16))
    # Quantity goals: how much was done that day (GP-46); null for binary goals.
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    goal: Mapped["Goal"] = relationship(back_populates="checkins")
