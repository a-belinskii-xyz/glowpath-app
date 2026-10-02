"""signup source on users and pending bot logins

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-10-02 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o9p0q1r2s3t4"
down_revision: Union[str, Sequence[str], None] = "n8o9p0q1r2s3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt_users", sa.Column("signup_source", sa.String(length=32), nullable=True))
    op.add_column(
        "mt_telegram_login_requests",
        sa.Column("signup_source", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mt_telegram_login_requests", "signup_source")
    op.drop_column("mt_users", "signup_source")
