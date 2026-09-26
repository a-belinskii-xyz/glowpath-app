"""add theme_preference to users

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-09-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, Sequence[str], None] = "i3j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_users",
        sa.Column(
            "theme_preference",
            sa.String(length=16),
            server_default="system",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck__mt_users__theme_preference_valid"),
        "mt_users",
        "theme_preference IN ('system', 'light', 'dark')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck__mt_users__theme_preference_valid"), "mt_users", type_="check")
    op.drop_column("mt_users", "theme_preference")
