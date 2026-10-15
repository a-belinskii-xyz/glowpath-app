"""weight measurements, food logs, body settings and food goals

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-10-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v6w7x8y9z0a1"
down_revision: str | Sequence[str] | None = "u5v6w7x8y9z0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "mt_measurements",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(5, 1), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "kind IN ('weight')", name=op.f("ck__mt_measurements__measurement_kind_values")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_measurements__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_measurements")),
        sa.UniqueConstraint(
            "user_id", "kind", "day", name=op.f("uq__mt_measurements__user_id_kind_day")
        ),
    )
    op.create_index(
        op.f("ix__mt_measurements__user_id"), "mt_measurements", ["user_id"], unique=False
    )

    op.create_table(
        "mt_food_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("meal", sa.String(length=16), nullable=True),
        sa.Column("text", sa.String(length=500), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "meal IS NULL OR meal IN ('morning', 'day', 'evening', 'snack')",
            name=op.f("ck__mt_food_logs__food_log_meal_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_food_logs__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_food_logs")),
    )
    op.create_index(op.f("ix__mt_food_logs__user_id"), "mt_food_logs", ["user_id"], unique=False)

    op.create_table(
        "mt_body_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("show_weight", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("show_food", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hide_weight", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_body_settings__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk__mt_body_settings")),
    )
    op.create_table(
        "mt_body_food_goals",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_body_food_goals__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["mt_goals.id"],
            name=op.f("fk__mt_body_food_goals__goal_id__mt_goals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "goal_id", name=op.f("pk__mt_body_food_goals")),
    )


def downgrade() -> None:
    op.drop_table("mt_body_food_goals")
    op.drop_table("mt_body_settings")
    op.drop_index(op.f("ix__mt_food_logs__user_id"), table_name="mt_food_logs")
    op.drop_table("mt_food_logs")
    op.drop_index(op.f("ix__mt_measurements__user_id"), table_name="mt_measurements")
    op.drop_table("mt_measurements")
