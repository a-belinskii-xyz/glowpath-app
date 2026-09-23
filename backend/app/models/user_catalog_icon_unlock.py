import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name, unique_index_name

if TYPE_CHECKING:
    from app.models.catalog_icon import CatalogIcon
    from app.models.user import User


class UserCatalogIconUnlock(TimestampMixin, Base):
    __tablename__ = table_name("user_catalog_icon_unlocks")
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "catalog_icon_id",
            name=unique_index_name("user_catalog_icon_unlocks", "user_icon"),
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
    catalog_icon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("catalog_icons"), ondelete="CASCADE"),
        index=True,
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )

    user: Mapped["User"] = relationship(back_populates="catalog_icon_unlocks")
    catalog_icon: Mapped["CatalogIcon"] = relationship()
