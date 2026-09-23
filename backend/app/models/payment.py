import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.billing import (
    BILLING_INTERVALS,
    PAYMENT_KINDS,
    PAYMENT_PROVIDER_IDS,
    PAYMENT_STATUSES,
)
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.names import fk_column, table_name

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.user_subscription import UserSubscription


_INTERVAL_SQL = ", ".join(f"'{item}'" for item in sorted(BILLING_INTERVALS))
_KIND_SQL = ", ".join(f"'{item}'" for item in sorted(PAYMENT_KINDS))
_PROVIDER_SQL = ", ".join(f"'{item}'" for item in sorted(PAYMENT_PROVIDER_IDS))
_STATUS_SQL = ", ".join(f"'{item}'" for item in sorted(PAYMENT_STATUSES))


class Payment(TimestampMixin, Base):
    __tablename__ = table_name("payments")
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="payment_status_values"),
        CheckConstraint(f"kind IN ({_KIND_SQL})", name="payment_kind_values"),
        CheckConstraint(f"provider IN ({_PROVIDER_SQL})", name="payment_provider_values"),
        CheckConstraint(
            f"billing_interval IN ({_INTERVAL_SQL})",
            name="payment_interval_values",
        ),
        CheckConstraint("amount_minor >= 0", name="payment_amount_non_negative"),
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
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk_column("user_subscriptions"), ondelete="SET NULL"),
        nullable=True,
    )
    plan_slug: Mapped[str] = mapped_column(String(32))
    billing_interval: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(String(32))
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), server_default="checkout")
    status: Mapped[str] = mapped_column(String(32), server_default="pending")
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    checkout_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    user: Mapped["User"] = relationship(back_populates="payments")
    subscription: Mapped["UserSubscription | None"] = relationship(back_populates="payments")
