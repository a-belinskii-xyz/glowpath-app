import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.default_tag_groups import (
    DEFAULT_TAG_COLOR,
    DEFAULT_TAG_ICON,
    DEFAULT_TAG_ICON_TYPE,
)
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.mood_entry_tag import MoodEntryTag
    from app.models.tag_group import TagGroup
    from app.models.user import User
    from app.models.user_tag_icon import UserTagIcon


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
    color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        server_default=DEFAULT_TAG_COLOR,
    )
    icon_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=DEFAULT_TAG_ICON_TYPE,
    )
    icon: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=DEFAULT_TAG_ICON,
    )
    # Set when this row was created by restoring an export archive (GP-20).
    restore_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("diary_restores"), ondelete="SET NULL"),
        nullable=True,
    )

    group: Mapped["TagGroup"] = relationship(back_populates="tags")
    user: Mapped["User"] = relationship()
    entry_links: Mapped[list["MoodEntryTag"]] = relationship(back_populates="tag")
    icons: Mapped[list["UserTagIcon"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
    )
