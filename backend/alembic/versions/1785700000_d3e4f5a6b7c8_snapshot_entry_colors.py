"""snapshot mood/tag/goal colors on entries

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-08-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_SCORE_COLORS = {
    1: "#64748b",
    2: "#94a3b8",
    3: "#60a5fa",
    4: "#34d399",
    5: "#f59e0b",
}


def upgrade() -> None:
    op.add_column(
        "mt_mood_entries",
        sa.Column("score_color", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "mt_mood_entry_tags",
        sa.Column("color", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "mt_mood_entry_goals",
        sa.Column("color", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "mt_user_mood_preferences",
        sa.Column(
            "use_historical_colors",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    score_fallback = " CASE e.score " + " ".join(
        f"WHEN {score} THEN '{color}'" for score, color in _DEFAULT_SCORE_COLORS.items()
    ) + " ELSE '#94a3b8' END"

    op.execute(
        sa.text(
            "UPDATE mt_mood_entries AS e "
            "SET score_color = COALESCE("
            "NULLIF(p.score_styles -> (e.score::text) ->> 'color', ''),"
            f"{score_fallback}"
            ") "
            "FROM mt_user_mood_preferences AS p "
            "WHERE p.user_id = e.user_id"
        )
    )
    op.execute(
        sa.text(
            "UPDATE mt_mood_entries AS e "
            f"SET score_color = {score_fallback} "
            "WHERE e.score_color IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE mt_mood_entry_tags AS link "
            "SET color = tag.color "
            "FROM mt_tags AS tag "
            "WHERE link.tag_id = tag.id"
        )
    )
    op.execute(
        sa.text(
            "UPDATE mt_mood_entry_goals AS link "
            "SET color = goal.color "
            "FROM mt_goals AS goal "
            "WHERE link.goal_id = goal.id"
        )
    )

    op.alter_column("mt_mood_entries", "score_color", nullable=False)
    op.alter_column("mt_mood_entry_tags", "color", nullable=False)
    op.alter_column("mt_mood_entry_goals", "color", nullable=False)


def downgrade() -> None:
    op.drop_column("mt_user_mood_preferences", "use_historical_colors")
    op.drop_column("mt_mood_entry_goals", "color")
    op.drop_column("mt_mood_entry_tags", "color")
    op.drop_column("mt_mood_entries", "score_color")
