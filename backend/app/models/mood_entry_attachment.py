import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.attachment_kind import AttachmentKind
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name, unique_index_name

if TYPE_CHECKING:
    from app.models.mood_entry import MoodEntry

MAX_PHOTOS_PER_ENTRY = 5


class MoodEntryAttachment(TimestampMixin, Base):
    __tablename__ = table_name("mood_entry_attachments")
    __table_args__ = (
        CheckConstraint(
            "(kind = 'photo' AND position BETWEEN 1 AND 10) OR "
            "(kind = 'audio' AND position IS NULL)",
            name="kind_position",
        ),
        Index(
            unique_index_name("mood_entry_attachments", "one_audio"),
            "mood_entry_id",
            unique=True,
            postgresql_where=text("kind = 'audio'"),
        ),
        Index(
            unique_index_name("mood_entry_attachments", "photo_position"),
            "mood_entry_id",
            "position",
            unique=True,
            postgresql_where=text("kind = 'photo'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    mood_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("mood_entries"), ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[AttachmentKind] = mapped_column(
        Enum(
            AttachmentKind,
            name="attachment_kind",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
    )
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int | None] = mapped_column(SmallInteger)
    # Filled later by local Whisper (or similar); used for note search over voice.
    transcription: Mapped[str | None] = mapped_column(Text)

    mood_entry: Mapped["MoodEntry"] = relationship(back_populates="attachments")
