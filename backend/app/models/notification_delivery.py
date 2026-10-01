import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.names import fk_column, index_name, table_name


class NotificationDelivery(Base):
    """One sent reminder (all channels of one schedule run share a row).

    ``engaged_at`` is set when the person follows the link from the reminder or makes
    an entry before the next reminder; a run of rows without it slows reminders down.
    """

    __tablename__ = table_name("notification_deliveries")
    __table_args__ = (
        Index(
            index_name("notification_deliveries", "schedule_id__sent_at"),
            "schedule_id",
            "sent_at",
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
        nullable=False,
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("user_notification_schedules"), ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String(16)), nullable=False)
    # Random value carried in reminder links (?n=…) to record a click without a session.
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    engaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
