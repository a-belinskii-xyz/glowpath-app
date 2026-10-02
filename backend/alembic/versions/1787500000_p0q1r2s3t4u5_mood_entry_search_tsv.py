"""full-text search vector on mood entry notes

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-10-02 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p0q1r2s3t4u5"
down_revision: Union[str, Sequence[str], None] = "o9p0q1r2s3t4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_mood_entries",
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('russian', coalesce(note, ''))", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix__mt_mood_entries__search_tsv",
        "mt_mood_entries",
        ["search_tsv"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix__mt_mood_entries__search_tsv", table_name="mt_mood_entries")
    op.drop_column("mt_mood_entries", "search_tsv")
