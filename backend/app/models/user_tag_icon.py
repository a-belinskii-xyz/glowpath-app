import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.user import User


class UserTagIcon(TimestampMixin, Base):
    __tablename__ = table_name("user_tag_icons")
    __table_args__ = (
        Index(
            index_name("user_tag_icons", "user_tag"),
            "user_id",
            "tag_id",
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
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("tags"), ondelete="CASCADE"),
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str] = mapped_column(String(255))
    source_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_mime_type: Mapped[str | None] = mapped_column(String(127), nullable=True)
    source_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship(back_populates="tag_icons")
    tag: Mapped["Tag"] = relationship(back_populates="icons")
