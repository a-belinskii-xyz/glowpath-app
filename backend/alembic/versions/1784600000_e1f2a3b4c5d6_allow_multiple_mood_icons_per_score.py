"""allow multiple mood icons per score

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-17 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq__mt_user_mood_icons__user_score", table_name="mt_user_mood_icons")
    op.create_index(
        "ix__mt_user_mood_icons__user_score",
        "mt_user_mood_icons",
        ["user_id", "score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix__mt_user_mood_icons__user_score", table_name="mt_user_mood_icons")
    op.create_index(
        "uq__mt_user_mood_icons__user_score",
        "mt_user_mood_icons",
        ["user_id", "score"],
        unique=True,
    )
