"""add logged_on snapshot for same-day streaks

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-08-27 16:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt_mood_entries", sa.Column("logged_on", sa.Date(), nullable=True))
    op.add_column(
        "mt_mood_entries",
        sa.Column("logged_timezone", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE mt_mood_entries AS e
            SET
                logged_timezone = u.timezone,
                logged_on = CASE
                    WHEN (e.created_at AT TIME ZONE u.timezone)::date
                        = (e.recorded_at AT TIME ZONE u.timezone)::date
                    THEN (e.recorded_at AT TIME ZONE u.timezone)::date
                    ELSE NULL
                END
            FROM mt_users AS u
            WHERE u.id = e.user_id
            """
        )
    )
    op.create_index(
        "ix__mt_mood_entries__user_id__logged_on",
        "mt_mood_entries",
        ["user_id", "logged_on"],
        postgresql_where=sa.text("logged_on IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix__mt_mood_entries__user_id__logged_on",
        table_name="mt_mood_entries",
    )
    op.drop_column("mt_mood_entries", "logged_timezone")
    op.drop_column("mt_mood_entries", "logged_on")
