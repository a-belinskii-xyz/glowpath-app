"""add goal show_in_stats

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-17 18:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Keep in sync with Settings.stats_visible_goal_limit default.
_STATS_VISIBLE_GOAL_LIMIT = 5


def upgrade() -> None:
    op.add_column(
        "mt_goals",
        sa.Column(
            "show_in_stats",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Pin the first N goals per user (by sort_order) so existing catalogs stay visible.
    op.execute(
        sa.text(
            f"""
            UPDATE mt_goals AS g
            SET show_in_stats = true
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id
                           ORDER BY sort_order, slug
                       ) AS rn
                FROM mt_goals
            ) AS ranked
            WHERE g.id = ranked.id
              AND ranked.rn <= {_STATS_VISIBLE_GOAL_LIMIT}
            """
        )
    )


def downgrade() -> None:
    op.drop_column("mt_goals", "show_in_stats")
