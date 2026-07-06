import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.mood_entry_tag import MoodEntryTag
    from app.models.tag_group import TagGroup
    from app.models.user import User


class Tag(TimestampMixin, Base):
    __tablename__ = table_name("tags")
    __table_args__ = (UniqueConstraint("group_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("tag_groups"), ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64))
    labels: Mapped[dict[str, str]] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")

    group: Mapped["TagGroup"] = relationship(back_populates="tags")
    user: Mapped["User"] = relationship()
    entry_links: Mapped[list["MoodEntryTag"]] = relationship(back_populates="tag")
