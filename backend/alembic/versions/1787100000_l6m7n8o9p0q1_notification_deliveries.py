"""notification deliveries and reminder backoff

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-10-01 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, Sequence[str], None] = "k5l6m7n8o9p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_notification_deliveries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("channels", postgresql.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("engaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_notification_deliveries__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["mt_user_notification_schedules.id"],
            name=op.f(
                "fk__mt_notification_deliveries__schedule_id__mt_user_notification_schedules"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_notification_deliveries")),
        sa.UniqueConstraint("token", name=op.f("uq__mt_notification_deliveries__token")),
    )
    op.create_index(
        "ix__mt_notification_deliveries__schedule_id__sent_at",
        "mt_notification_deliveries",
        ["schedule_id", "sent_at"],
        unique=False,
    )
    op.add_column(
        "mt_user_notification_schedules",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mt_user_notification_schedules",
        sa.Column("backoff_reset_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mt_user_notification_schedules", "backoff_reset_at")
    op.drop_column("mt_user_notification_schedules", "paused_at")
    op.drop_index(
        "ix__mt_notification_deliveries__schedule_id__sent_at",
        table_name="mt_notification_deliveries",
    )
    op.drop_table("mt_notification_deliveries")
