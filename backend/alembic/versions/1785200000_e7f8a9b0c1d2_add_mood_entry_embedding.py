"""add mood entry embedding for semantic search

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-19 18:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMS = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "mt_mood_entries",
        sa.Column("embedding", Vector(EMBEDDING_DIMS), nullable=True),
    )
    op.create_index(
        "ix__mt_mood_entries__embedding_hnsw",
        "mt_mood_entries",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix__mt_mood_entries__embedding_hnsw", table_name="mt_mood_entries")
    op.drop_column("mt_mood_entries", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
