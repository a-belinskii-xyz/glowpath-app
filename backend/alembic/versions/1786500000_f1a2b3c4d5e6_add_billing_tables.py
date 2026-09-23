"""billing subscriptions and payments

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-09-01 03:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_slug", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("billing_interval", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'canceled', 'expired', 'past_due', 'trialing')",
            name="user_subscription_status_values",
        ),
        sa.CheckConstraint(
            "billing_interval IN ('month', 'year')",
            name="user_subscription_interval_values",
        ),
        sa.CheckConstraint(
            "provider IN ('fake', 'sber', 'stripe')",
            name="user_subscription_provider_values",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "mt_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_slug", sa.String(length=32), nullable=False),
        sa.Column("billing_interval", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_session_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("kind", sa.String(length=32), server_default="checkout", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("checkout_url", sa.String(length=2048), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('canceled', 'failed', 'pending', 'refunded', 'succeeded')",
            name="payment_status_values",
        ),
        sa.CheckConstraint(
            "kind IN ('checkout', 'refund', 'renewal')",
            name="payment_kind_values",
        ),
        sa.CheckConstraint(
            "provider IN ('fake', 'sber', 'stripe')",
            name="payment_provider_values",
        ),
        sa.CheckConstraint(
            "billing_interval IN ('month', 'year')",
            name="payment_interval_values",
        ),
        sa.CheckConstraint("amount_minor >= 0", name="payment_amount_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["mt_user_subscriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mt_payments_user_id", "mt_payments", ["user_id"])
    op.create_index(
        "ix__mt_payments__provider_session",
        "mt_payments",
        ["provider", "provider_session_id"],
    )
    op.create_table(
        "mt_payment_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq__mt_payment_webhook_events__provider_event",
        ),
    )


def downgrade() -> None:
    op.drop_table("mt_payment_webhook_events")
    op.drop_index("ix__mt_payments__provider_session", table_name="mt_payments")
    op.drop_index("ix_mt_payments_user_id", table_name="mt_payments")
    op.drop_table("mt_payments")
    op.drop_table("mt_user_subscriptions")
