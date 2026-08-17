import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.mood_entry import MoodEntry
    from app.models.tag import Tag


class MoodEntryTag(Base):
    __tablename__ = table_name("mood_entry_tags")

    mood_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("mood_entries"), ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("tags"), ondelete="RESTRICT"),
        primary_key=True,
    )
    color: Mapped[str] = mapped_column(String(7))

    mood_entry: Mapped["MoodEntry"] = relationship(back_populates="tag_links")
    tag: Mapped["Tag"] = relationship(back_populates="entry_links")
