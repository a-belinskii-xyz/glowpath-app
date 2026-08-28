import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.visitor import Visitor


class GuestAuthEvent(StrEnum):
    NONE = "none"
    IMPORTED = "imported"
    EXISTING_LOGIN_SKIPPED = "existing_login_skipped"


class GuestDevice(TimestampMixin, Base):
    __tablename__ = table_name("guest_devices")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("visitors"), ondelete="CASCADE"),
        primary_key=True,
    )
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    entry_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(
        server_default=text("false"),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    converted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("users"), ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_auth_event: Mapped[str] = mapped_column(
        String(32),
        server_default=GuestAuthEvent.NONE.value,
        nullable=False,
    )

    visitor: Mapped["Visitor"] = relationship(foreign_keys=[id])
    converted_user: Mapped["User | None"] = relationship(foreign_keys=[converted_user_id])
