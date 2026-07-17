import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.user import User


class UserMoodPreferences(TimestampMixin, Base):
    __tablename__ = table_name("user_mood_preferences")

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="CASCADE"),
        primary_key=True,
    )
    score_styles: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship(back_populates="mood_preferences")
