"""add time_format to users

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-10-15 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "y9z0a1b2c3d4"
down_revision: str | Sequence[str] | None = "x8y9z0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mt_users",
        sa.Column("time_format", sa.String(length=8), server_default="auto", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck__mt_users__time_format_valid"),
        "mt_users",
        "time_format IN ('auto', '24h', '12h')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck__mt_users__time_format_valid"), "mt_users", type_="check")
    op.drop_column("mt_users", "time_format")
