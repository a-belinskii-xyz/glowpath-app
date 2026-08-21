"""user achievement unlock source entry + indexes

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-08-21 19:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_user_achievements",
        sa.Column("unlocked_by_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_mt_user_achievements_unlocked_by_entry_id",
        "mt_user_achievements",
        "mt_mood_entries",
        ["unlocked_by_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_mt_user_achievements_unlocked_by_entry_id",
        "mt_user_achievements",
        ["unlocked_by_entry_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mt_user_achievements_unlocked_by_entry_id",
        table_name="mt_user_achievements",
    )
    op.drop_constraint(
        "fk_mt_user_achievements_unlocked_by_entry_id",
        "mt_user_achievements",
        type_="foreignkey",
    )
    op.drop_column("mt_user_achievements", "unlocked_by_entry_id")
