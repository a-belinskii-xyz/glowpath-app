import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.billing import BILLING_INTERVALS, PAYMENT_PROVIDER_IDS, SUBSCRIPTION_STATUSES
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.user import User


_INTERVAL_SQL = ", ".join(f"'{item}'" for item in sorted(BILLING_INTERVALS))
_PROVIDER_SQL = ", ".join(f"'{item}'" for item in sorted(PAYMENT_PROVIDER_IDS))
_STATUS_SQL = ", ".join(f"'{item}'" for item in sorted(SUBSCRIPTION_STATUSES))


class UserSubscription(TimestampMixin, Base):
    __tablename__ = table_name("user_subscriptions")
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="user_subscription_status_values"),
        CheckConstraint(
            f"billing_interval IN ({_INTERVAL_SQL})",
            name="user_subscription_interval_values",
        ),
        CheckConstraint(
            f"provider IN ({_PROVIDER_SQL})",
            name="user_subscription_provider_values",
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
        unique=True,
    )
    plan_slug: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), server_default="active")
    billing_interval: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(32))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")
