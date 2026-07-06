import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name

if TYPE_CHECKING:
    from app.models.mood_entry_attachment import MoodEntryAttachment
    from app.models.mood_entry_tag import MoodEntryTag
    from app.models.user import User


class MoodEntry(TimestampMixin, Base):
    __tablename__ = table_name("mood_entries")
    __table_args__ = (
        CheckConstraint(
            f"score >= {MIN_MOOD_SCORE} AND score <= {MAX_MOOD_SCORE}",
            name="score_range",
        ),
        Index(
            index_name("mood_entries", "user_id__recorded_at"),
            "user_id",
            "recorded_at",
            postgresql_ops={"recorded_at": "DESC"},
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
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(String(500))

    user: Mapped["User"] = relationship(back_populates="mood_entries")
    tag_links: Mapped[list["MoodEntryTag"]] = relationship(
        back_populates="mood_entry",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["MoodEntryAttachment"]] = relationship(
        back_populates="mood_entry",
        cascade="all, delete-orphan",
    )
