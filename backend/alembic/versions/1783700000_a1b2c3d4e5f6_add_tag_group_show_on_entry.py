"""add tag group show_on_entry

Revision ID: a1b2c3d4e5f6
Revises: b97d2877b711
Create Date: 2026-07-10 17:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b97d2877b711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_tag_groups",
        sa.Column(
            "show_on_entry",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE mt_tag_groups
        SET show_on_entry = true
        WHERE slug IN ('weather', 'sleep_quality', 'mood', 'activity')
        """
    )


def downgrade() -> None:
    op.drop_column("mt_tag_groups", "show_on_entry")
