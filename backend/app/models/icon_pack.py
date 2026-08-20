import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.catalog_icon import CatalogIcon
    from app.models.user import User


class IconPack(TimestampMixin, Base):
    __tablename__ = table_name("icon_packs")
    __table_args__ = (
        CheckConstraint("price_tokens >= 0", name="icon_pack_price_non_negative"),
        CheckConstraint(
            "status IN ("
            "'draft', 'pending_review', 'rejected', 'published', 'archived'"
            ")",
            name="icon_pack_status_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_official: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    status: Mapped[str] = mapped_column(String(32), server_default="draft")
    price_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    labels: Mapped[dict] = mapped_column(JSONB)
    cover_icon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("catalog_icons"), ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderation_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="SET NULL"),
        nullable=True,
    )

    author: Mapped["User | None"] = relationship(
        back_populates="authored_icon_packs",
        foreign_keys=[author_id],
    )
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by])
    icons: Mapped[list["CatalogIcon"]] = relationship(
        back_populates="pack",
        cascade="all, delete-orphan",
        foreign_keys="CatalogIcon.pack_id",
        order_by="CatalogIcon.sort_order",
    )
    cover_icon: Mapped["CatalogIcon | None"] = relationship(
        foreign_keys=[cover_icon_id],
        post_update=True,
    )
