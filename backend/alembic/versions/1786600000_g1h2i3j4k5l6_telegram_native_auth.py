"""allow telegram-native users without email

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-09-08 17:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck__mt_users__auth_method_present"), "mt_users", type_="check")
    op.alter_column("mt_users", "email", existing_type=sa.String(length=320), nullable=True)
    op.create_check_constraint(
        "auth_method_present",
        "mt_users",
        "password_hash IS NOT NULL OR google_sub IS NOT NULL OR telegram_user_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck__mt_users__auth_method_present"), "mt_users", type_="check")
    op.alter_column("mt_users", "email", existing_type=sa.String(length=320), nullable=False)
    op.create_check_constraint(
        "auth_method_present",
        "mt_users",
        "password_hash IS NOT NULL OR google_sub IS NOT NULL",
    )
