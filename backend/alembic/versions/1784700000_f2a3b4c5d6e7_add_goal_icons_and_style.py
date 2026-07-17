"""add goal icons and style

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-17 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_goals",
        sa.Column("color", sa.String(length=7), server_default="#60a5fa", nullable=False),
    )
    op.add_column(
        "mt_goals",
        sa.Column("icon_type", sa.String(length=16), server_default="emoji", nullable=False),
    )
    op.add_column(
        "mt_goals",
        sa.Column("icon", sa.String(length=64), server_default="🎯", nullable=False),
    )

    op.create_table(
        "mt_user_goal_icons",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
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
        sa.ForeignKeyConstraint(["goal_id"], ["mt_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix__mt_user_goal_icons__user_goal",
        "mt_user_goal_icons",
        ["user_id", "goal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mt_user_goal_icons_user_id"),
        "mt_user_goal_icons",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mt_user_goal_icons_goal_id"),
        "mt_user_goal_icons",
        ["goal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_mt_user_goal_icons_goal_id"), table_name="mt_user_goal_icons")
    op.drop_index(op.f("ix_mt_user_goal_icons_user_id"), table_name="mt_user_goal_icons")
    op.drop_index("ix__mt_user_goal_icons__user_goal", table_name="mt_user_goal_icons")
    op.drop_table("mt_user_goal_icons")
    op.drop_column("mt_goals", "icon")
    op.drop_column("mt_goals", "icon_type")
    op.drop_column("mt_goals", "color")
