"""create goals tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-15 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_goals",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("times_per_week", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "show_on_entry",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
            "times_per_week >= 1 AND times_per_week <= 7",
            name="times_per_week_range",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slug"),
    )
    op.create_index("ix__mt_goals__user_id", "mt_goals", ["user_id"])

    op.create_table(
        "mt_mood_entry_goals",
        sa.Column("mood_entry_id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["mt_goals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mood_entry_id"], ["mt_mood_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mood_entry_id", "goal_id"),
    )


def downgrade() -> None:
    op.drop_table("mt_mood_entry_goals")
    op.drop_index("ix__mt_goals__user_id", table_name="mt_goals")
    op.drop_table("mt_goals")
