"""mood entry client key: one entry per Telegram message tapped

Revision ID: c2d3e4f5a6b8
Revises: b1c2d3e4f5a7
Create Date: 2026-11-10 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b8"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mt_mood_entries", sa.Column("client_key", sa.String(64), nullable=True))
    op.create_index(
        "uq__mt_mood_entries__user_id__client_key",
        "mt_mood_entries",
        ["user_id", "client_key"],
        unique=True,
        postgresql_where=sa.text("client_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq__mt_mood_entries__user_id__client_key",
        table_name="mt_mood_entries",
        postgresql_where=sa.text("client_key IS NOT NULL"),
    )
    op.drop_column("mt_mood_entries", "client_key")
