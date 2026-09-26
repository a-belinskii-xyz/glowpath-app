import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import table_name
from app.models.catalog_icon_search_tag import CatalogIconSearchTag  # noqa: F401

if TYPE_CHECKING:
    from app.models.catalog_icon import CatalogIcon


class IconSearchTag(TimestampMixin, Base):
    __tablename__ = table_name("icon_search_tags")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    icons: Mapped[list["CatalogIcon"]] = relationship(
        secondary=table_name("catalog_icon_search_tags"),
        back_populates="search_tags",
        lazy="selectin",
    )
