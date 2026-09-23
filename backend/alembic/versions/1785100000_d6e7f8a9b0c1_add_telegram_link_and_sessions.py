"""add telegram link columns, link codes, and sessions

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-18 22:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt_users", sa.Column("telegram_user_id", sa.BigInteger(), nullable=True))
    op.add_column("mt_users", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "mt_users",
        sa.Column("telegram_linked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("mt_users", sa.Column("telegram_locale", sa.String(length=16), nullable=True))
    op.create_unique_constraint(
        op.f("uq__mt_users__telegram_user_id"),
        "mt_users",
        ["telegram_user_id"],
    )
    op.create_check_constraint(
        op.f("ck__mt_users__telegram_link_complete"),
        "mt_users",
        "("
        "telegram_user_id IS NULL AND telegram_chat_id IS NULL "
        "AND telegram_linked_at IS NULL"
        ") OR ("
        "telegram_user_id IS NOT NULL AND telegram_chat_id IS NOT NULL "
        "AND telegram_linked_at IS NOT NULL"
        ")",
    )

    op.create_table(
        "mt_telegram_link_codes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_telegram_link_codes__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_telegram_link_codes")),
    )
    op.create_index(
        op.f("ix__mt_telegram_link_codes__user_id"),
        "mt_telegram_link_codes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix__mt_telegram_link_codes__code_hash__active"),
        "mt_telegram_link_codes",
        ["code_hash"],
        unique=False,
        postgresql_where=sa.text("used_at IS NULL"),
    )

    op.create_table(
        "mt_telegram_sessions",
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("telegram_user_id", name=op.f("pk__mt_telegram_sessions")),
    )


def downgrade() -> None:
    op.drop_table("mt_telegram_sessions")
    op.drop_index(
        op.f("ix__mt_telegram_link_codes__code_hash__active"),
        table_name="mt_telegram_link_codes",
        postgresql_where=sa.text("used_at IS NULL"),
    )
    op.drop_index(
        op.f("ix__mt_telegram_link_codes__user_id"),
        table_name="mt_telegram_link_codes",
    )
    op.drop_table("mt_telegram_link_codes")
    op.drop_constraint(op.f("ck__mt_users__telegram_link_complete"), "mt_users", type_="check")
    op.drop_constraint(op.f("uq__mt_users__telegram_user_id"), "mt_users", type_="unique")
    op.drop_column("mt_users", "telegram_locale")
    op.drop_column("mt_users", "telegram_linked_at")
    op.drop_column("mt_users", "telegram_chat_id")
    op.drop_column("mt_users", "telegram_user_id")
