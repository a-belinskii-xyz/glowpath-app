import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.goal import Goal
    from app.models.mood_entry import MoodEntry


class MoodEntryGoal(Base):
    __tablename__ = table_name("mood_entry_goals")

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

    mood_entry: Mapped["MoodEntry"] = relationship(back_populates="goal_links")
    goal: Mapped["Goal"] = relationship(back_populates="entry_links")
