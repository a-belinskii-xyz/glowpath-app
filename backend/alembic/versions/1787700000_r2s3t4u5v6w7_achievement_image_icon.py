"""achievement image icon

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-10-02 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r2s3t4u5v6w7"
down_revision: Union[str, Sequence[str], None] = "q1r2s3t4u5v6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_achievements",
        sa.Column("icon_storage_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "mt_achievements",
        sa.Column("icon_mime_type", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck__mt_achievements__achievement_icon_type_values"),
        "mt_achievements",
        "icon_type IN ('emoji', 'image')",
    )
    op.create_check_constraint(
        op.f("ck__mt_achievements__achievement_image_icon_fields"),
        "mt_achievements",
        "icon_type <> 'image' OR (icon_storage_key IS NOT NULL AND icon_mime_type IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck__mt_achievements__achievement_image_icon_fields"), "mt_achievements", type_="check"
    )
    op.drop_constraint(
        op.f("ck__mt_achievements__achievement_icon_type_values"), "mt_achievements", type_="check"
    )
    op.drop_column("mt_achievements", "icon_mime_type")
    op.drop_column("mt_achievements", "icon_storage_key")
