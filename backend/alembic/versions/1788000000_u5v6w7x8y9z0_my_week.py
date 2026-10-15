"""wins marker, goal min amount, check-in amount

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-10-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "u5v6w7x8y9z0"
down_revision: str | Sequence[str] | None = "t4u5v6w7x8y9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mt_mood_entries",
        sa.Column("is_win", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("mt_goals", sa.Column("min_amount", sa.Integer(), nullable=True))
    op.add_column("mt_goal_checkins", sa.Column("amount", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("mt_goal_checkins", "amount")
    op.drop_column("mt_goals", "min_amount")
    op.drop_column("mt_mood_entries", "is_win")
