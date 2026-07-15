"""add mood entry is_favorite

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-14 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_mood_entries",
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix__mt_mood_entries__user_id__is_favorite",
        "mt_mood_entries",
        ["user_id", "is_favorite"],
    )


def downgrade() -> None:
    op.drop_index("ix__mt_mood_entries__user_id__is_favorite", table_name="mt_mood_entries")
    op.drop_column("mt_mood_entries", "is_favorite")
