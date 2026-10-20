"""the person's own sleep norm for colouring nights

Revision ID: b1c2d3e4f5a7
Revises: a0b1c2d3e4f5
Create Date: 2026-10-20 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a7"
down_revision: str | Sequence[str] | None = "a0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mt_body_settings",
        sa.Column("sleep_norm_min", sa.Integer(), server_default="420", nullable=True),
    )
    op.add_column(
        "mt_body_settings",
        sa.Column("sleep_norm_max", sa.Integer(), server_default="540", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mt_body_settings", "sleep_norm_max")
    op.drop_column("mt_body_settings", "sleep_norm_min")
