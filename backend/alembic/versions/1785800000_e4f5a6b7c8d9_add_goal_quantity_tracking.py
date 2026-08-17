"""add goal quantity tracking and entry amounts

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-17 15:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_goals",
        sa.Column(
            "tracking_kind",
            sa.String(length=16),
            server_default="binary",
            nullable=False,
        ),
    )
    op.add_column(
        "mt_goals",
        sa.Column("target_amount", sa.Integer(), nullable=True),
    )
    op.add_column(
        "mt_goals",
        sa.Column("unit", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "goal_tracking_kind_values",
        "mt_goals",
        "tracking_kind IN ('binary', 'quantity')",
    )
    op.create_check_constraint(
        "goal_quantity_fields",
        "mt_goals",
        "(tracking_kind = 'binary' AND target_amount IS NULL AND unit IS NULL) "
        "OR (tracking_kind = 'quantity' AND target_amount >= 1)",
    )

    op.add_column(
        "mt_mood_entry_goals",
        sa.Column("amount", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "mood_entry_goal_amount_positive",
        "mt_mood_entry_goals",
        "amount IS NULL OR amount >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "mood_entry_goal_amount_positive",
        "mt_mood_entry_goals",
        type_="check",
    )
    op.drop_column("mt_mood_entry_goals", "amount")
    op.drop_constraint("goal_quantity_fields", "mt_goals", type_="check")
    op.drop_constraint("goal_tracking_kind_values", "mt_goals", type_="check")
    op.drop_column("mt_goals", "unit")
    op.drop_column("mt_goals", "target_amount")
    op.drop_column("mt_goals", "tracking_kind")
