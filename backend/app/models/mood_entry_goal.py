import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.goal import Goal
    from app.models.mood_entry import MoodEntry


class MoodEntryGoal(Base):
    __tablename__ = table_name("mood_entry_goals")
    __table_args__ = (
        CheckConstraint("amount IS NULL OR amount >= 1", name="mood_entry_goal_amount_positive"),
    )

    mood_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("mood_entries"), ondelete="CASCADE"),
        primary_key=True,
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("goals"), ondelete="RESTRICT"),
        primary_key=True,
    )
    color: Mapped[str] = mapped_column(String(7))
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Binary goals: the entry did «немного» of the goal, not all of it (GP-51).
    is_partial: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    mood_entry: Mapped["MoodEntry"] = relationship(back_populates="goal_links")
    goal: Mapped["Goal"] = relationship(back_populates="entry_links")
