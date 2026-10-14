"""goal checkins and partial label

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-10-14 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s3t4u5v6w7x8"
down_revision: Union[str, Sequence[str], None] = "r2s3t4u5v6w7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt_goals", sa.Column("partial_label", sa.String(length=80), nullable=True))
    op.create_table(
        "mt_goal_checkins",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
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
            "level IN ('partial', 'full')",
            name=op.f("ck__mt_goal_checkins__goal_checkin_level_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_goal_checkins__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["mt_goals.id"],
            name=op.f("fk__mt_goal_checkins__goal_id__mt_goals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_goal_checkins")),
        sa.UniqueConstraint("goal_id", "day", name=op.f("uq__mt_goal_checkins__goal_id_day")),
    )
    op.create_index(
        op.f("ix__mt_goal_checkins__user_id"), "mt_goal_checkins", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix__mt_goal_checkins__user_id"), table_name="mt_goal_checkins")
    op.drop_table("mt_goal_checkins")
    op.drop_column("mt_goals", "partial_label")
