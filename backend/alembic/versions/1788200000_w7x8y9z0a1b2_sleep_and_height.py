"""sleep logs, sleep toggle and height for BMI

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-10-15 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "w7x8y9z0a1b2"
down_revision: str | Sequence[str] | None = "v6w7x8y9z0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mt_body_settings",
        sa.Column("show_sleep", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("mt_body_settings", sa.Column("height_cm", sa.Numeric(4, 1), nullable=True))
    op.create_table(
        "mt_sleep_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("bed_time", sa.Time(), nullable=False),
        sa.Column("wake_time", sa.Time(), nullable=False),
        sa.Column("up_time", sa.Time(), nullable=True),
        sa.Column("quality", sa.String(length=8), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quality IS NULL OR quality IN ('hard', 'ok', 'good')",
            name=op.f("ck__mt_sleep_logs__sleep_log_quality_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_sleep_logs__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_sleep_logs")),
        sa.UniqueConstraint("user_id", "day", name=op.f("uq__mt_sleep_logs__user_id_day")),
    )
    op.create_index(op.f("ix__mt_sleep_logs__user_id"), "mt_sleep_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix__mt_sleep_logs__user_id"), table_name="mt_sleep_logs")
    op.drop_table("mt_sleep_logs")
    op.drop_column("mt_body_settings", "height_cm")
    op.drop_column("mt_body_settings", "show_sleep")
