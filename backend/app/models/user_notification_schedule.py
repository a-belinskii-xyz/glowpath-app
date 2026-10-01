import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name, unique_index_name

if TYPE_CHECKING:
    from app.models.user import User


class UserNotificationSchedule(TimestampMixin, Base):
    """One reminder schedule per user and kind (mood check-in, goals, …)."""

    __tablename__ = table_name("user_notification_schedules")
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "kind",
            name=unique_index_name("user_notification_schedules", "user_id_kind"),
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
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    time_of_day: Mapped[str] = mapped_column(String(5), nullable=False)
    interval_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    days_of_week: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    channels: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)),
        nullable=False,
        server_default=text("ARRAY['telegram']::varchar[]"),
    )
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when ignored reminders stopped this schedule; cleared when the person turns it on.
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Deliveries before this moment no longer count towards the ignored streak.
    backoff_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="notification_schedules")
