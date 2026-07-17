"""add goal ends_on

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-17 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt_goals", sa.Column("ends_on", sa.Date(), nullable=True))
    op.create_check_constraint(
        "goal_ends_on_after_starts_on",
        "mt_goals",
        "ends_on IS NULL OR ends_on >= starts_on",
    )


def downgrade() -> None:
    op.drop_constraint("goal_ends_on_after_starts_on", "mt_goals", type_="check")
    op.drop_column("mt_goals", "ends_on")
