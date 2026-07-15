"""add mood entry source for notification attribution

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_mood_entries",
        sa.Column("source", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix__mt_mood_entries__user_id__source",
        "mt_mood_entries",
        ["user_id", "source"],
    )


def downgrade() -> None:
    op.drop_index("ix__mt_mood_entries__user_id__source", table_name="mt_mood_entries")
    op.drop_column("mt_mood_entries", "source")
