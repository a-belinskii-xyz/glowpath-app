import uuid

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.names import fk_column, table_name


class CatalogIconSearchTag(Base):
    """M2M join between catalog icons and controlled search-tag vocabulary."""

    __tablename__ = table_name("catalog_icon_search_tags")
    __table_args__ = (PrimaryKeyConstraint("icon_id", "tag_id"),)

    icon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("catalog_icons"), ondelete="CASCADE"),
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("icon_search_tags"), ondelete="CASCADE"),
    )
