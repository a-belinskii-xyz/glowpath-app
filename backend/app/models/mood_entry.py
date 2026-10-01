import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mood_scale import MAX_MOOD_SCORE, MIN_MOOD_SCORE
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name

EMBEDDING_DIMS = 384


if TYPE_CHECKING:
    from app.models.mood_entry_attachment import MoodEntryAttachment
    from app.models.mood_entry_goal import MoodEntryGoal
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
        Index(
            index_name("mood_entries", "user_id__is_favorite"),
            "user_id",
            "is_favorite",
        ),
        Index(
            index_name("mood_entries", "user_id__source"),
            "user_id",
            "source",
        ),
        Index(
            index_name("mood_entries", "user_id__origin_id"),
            "user_id",
            "origin_id",
            postgresql_where=text("origin_id IS NOT NULL"),
        ),
        Index(
            index_name("mood_entries", "user_id__logged_on"),
            "user_id",
            "logged_on",
            postgresql_where=text("logged_on IS NOT NULL"),
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
    # Civil day this entry counts toward a streak, frozen in logged_timezone.
    # Null when the entry was written on a different local day than recorded_at.
    logged_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    logged_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int] = mapped_column(SmallInteger)
    # Mood palette color at create / score-change time (not live preferences).
    score_color: Mapped[str] = mapped_column(String(7))
    note: Mapped[str | None] = mapped_column(Text)
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    # Attribution for analytics, ``{channel}:{kind}`` (e.g. email:daily_mood_reminder);
    # not shown in UI.
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Set when this row was created by restoring an export archive (GP-20).
    restore_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("diary_restores"), ondelete="SET NULL"),
        nullable=True,
    )
    # Id the entry had in the archive it was restored from; restores skip it next time.
    origin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Semantic search vector (fastembed); null when entry has no searchable text.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMS), nullable=True)

    user: Mapped["User"] = relationship(back_populates="mood_entries")
    tag_links: Mapped[list["MoodEntryTag"]] = relationship(
        back_populates="mood_entry",
        cascade="all, delete-orphan",
    )
    goal_links: Mapped[list["MoodEntryGoal"]] = relationship(
        back_populates="mood_entry",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["MoodEntryAttachment"]] = relationship(
        back_populates="mood_entry",
        cascade="all, delete-orphan",
    )
