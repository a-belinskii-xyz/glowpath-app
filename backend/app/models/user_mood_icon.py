import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, index_name, table_name

if TYPE_CHECKING:
    from app.models.user import User


class UserMoodIcon(TimestampMixin, Base):
    __tablename__ = table_name("user_mood_icons")
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),
        Index(
            index_name("user_mood_icons", "user_score"),
            "user_id",
            "score",
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
    score: Mapped[int] = mapped_column(SmallInteger)
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="mood_icons")
