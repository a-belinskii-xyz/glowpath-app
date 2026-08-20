import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name, unique_index_name
from app.models.catalog_icon_search_tag import CatalogIconSearchTag  # noqa: F401

if TYPE_CHECKING:
    from app.models.icon_pack import IconPack
    from app.models.icon_search_tag import IconSearchTag


class CatalogIcon(TimestampMixin, Base):
    __tablename__ = table_name("catalog_icons")
    __table_args__ = (
        Index(
            unique_index_name("catalog_icons", "pack_slug"),
            "pack_id",
            "slug",
            unique=True,
        ),
        Index(index_name("catalog_icons", "pack_sort"), "pack_id", "sort_order"),
        CheckConstraint(
            "size_bytes >= 0",
            name="catalog_icon_size_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("icon_packs"), ondelete="CASCADE"),
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64))
    labels: Mapped[dict] = mapped_column(JSONB)
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    suggested_colors: Mapped[list] = mapped_column(JSONB)
    suggested_mood_scores: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger),
        server_default=text("'{}'::smallint[]"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    pack: Mapped["IconPack"] = relationship(
        back_populates="icons",
        foreign_keys=[pack_id],
    )
    search_tags: Mapped[list["IconSearchTag"]] = relationship(
        secondary=table_name("catalog_icon_search_tags"),
        back_populates="icons",
        lazy="selectin",
    )
