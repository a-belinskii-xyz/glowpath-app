"""add icon source storage for recrop

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-07-28 14:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ICON_TABLES = (
    "mt_user_mood_icons",
    "mt_user_goal_icons",
    "mt_user_tag_icons",
)


def upgrade() -> None:
    for table in _ICON_TABLES:
        op.add_column(table, sa.Column("source_storage_key", sa.String(length=512), nullable=True))
        op.add_column(table, sa.Column("source_mime_type", sa.String(length=127), nullable=True))
        op.add_column(table, sa.Column("source_size_bytes", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    for table in reversed(_ICON_TABLES):
        op.drop_column(table, "source_size_bytes")
        op.drop_column(table, "source_mime_type")
        op.drop_column(table, "source_storage_key")
