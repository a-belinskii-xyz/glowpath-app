"""calendar from start

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-10-14 23:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t4u5v6w7x8y9"
down_revision: Union[str, Sequence[str], None] = "s3t4u5v6w7x8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_user_mood_preferences",
        sa.Column(
            "calendar_from_start",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "mt_user_mood_preferences", sa.Column("calendar_start_on", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("mt_user_mood_preferences", "calendar_start_on")
    op.drop_column("mt_user_mood_preferences", "calendar_from_start")
