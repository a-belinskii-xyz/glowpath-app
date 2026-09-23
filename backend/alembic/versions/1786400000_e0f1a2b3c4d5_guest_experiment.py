"""guest experiment visitors and guest devices

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-08-28 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_visitors",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=True),
        sa.Column("cohort", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("converted_user_id", sa.UUID(), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["converted_user_id"], ["mt_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint_hash"),
    )
    op.create_index(
        "ix__mt_visitors__converted_user_id",
        "mt_visitors",
        ["converted_user_id"],
    )

    op.create_table(
        "mt_guest_devices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("entry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("converted_user_id", sa.UUID(), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_auth_event", sa.String(length=32), server_default="none", nullable=False),
        sa.ForeignKeyConstraint(["id"], ["mt_visitors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["converted_user_id"], ["mt_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix__mt_guest_devices__converted_user_id",
        "mt_guest_devices",
        ["converted_user_id"],
    )

    op.add_column("mt_users", sa.Column("pending_guest_device_id", sa.UUID(), nullable=True))
    op.add_column("mt_users", sa.Column("guest_imported_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk__mt_users__pending_guest_device_id__mt_visitors",
        "mt_users",
        "mt_visitors",
        ["pending_guest_device_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk__mt_users__pending_guest_device_id__mt_visitors",
        "mt_users",
        type_="foreignkey",
    )
    op.drop_column("mt_users", "guest_imported_at")
    op.drop_column("mt_users", "pending_guest_device_id")
    op.drop_index("ix__mt_guest_devices__converted_user_id", table_name="mt_guest_devices")
    op.drop_table("mt_guest_devices")
    op.drop_index("ix__mt_visitors__converted_user_id", table_name="mt_visitors")
    op.drop_table("mt_visitors")
