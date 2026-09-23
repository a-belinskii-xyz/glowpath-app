"""icon marketplace tables and user is_staff

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-21 02:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mt_users",
        sa.Column(
            "is_staff",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.create_table(
        "mt_icon_search_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "mt_icon_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_official", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("price_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cover_icon_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_note", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("price_tokens >= 0", name="icon_pack_price_non_negative"),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'rejected', 'published', 'archived')",
            name="icon_pack_status_values",
        ),
        sa.ForeignKeyConstraint(["author_id"], ["mt_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["mt_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_mt_icon_packs_author_id", "mt_icon_packs", ["author_id"])

    op.create_table(
        "mt_catalog_icons",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("suggested_colors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "suggested_mood_scores",
            postgresql.ARRAY(sa.SmallInteger()),
            server_default=sa.text("'{}'::smallint[]"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("size_bytes >= 0", name="catalog_icon_size_non_negative"),
        sa.ForeignKeyConstraint(["pack_id"], ["mt_icon_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mt_catalog_icons_pack_id", "mt_catalog_icons", ["pack_id"])
    op.create_index(
        "uq__mt_catalog_icons__pack_slug",
        "mt_catalog_icons",
        ["pack_id", "slug"],
        unique=True,
    )
    op.create_index(
        "ix__mt_catalog_icons__pack_sort",
        "mt_catalog_icons",
        ["pack_id", "sort_order"],
    )

    op.create_foreign_key(
        "fk_mt_icon_packs_cover_icon_id",
        "mt_icon_packs",
        "mt_catalog_icons",
        ["cover_icon_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "mt_catalog_icon_search_tags",
        sa.Column("icon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["icon_id"], ["mt_catalog_icons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["mt_icon_search_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("icon_id", "tag_id"),
    )

    op.create_table(
        "mt_user_wallets",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balance", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("balance >= 0", name="user_wallet_balance_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "mt_wallet_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delta", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('grant', 'unlock_pack', 'adjustment', 'refund')",
            name="wallet_ledger_kind_values",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["mt_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pack_id"], ["mt_icon_packs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mt_wallet_ledger_user_id", "mt_wallet_ledger", ["user_id"])
    op.create_index(
        "ix__mt_wallet_ledger__user_created",
        "mt_wallet_ledger",
        ["user_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    op.create_table(
        "mt_icon_pack_unlocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pack_id"], ["mt_icon_packs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "pack_id", name="uq__mt_icon_pack_unlocks__user_pack"),
    )
    op.create_index("ix_mt_icon_pack_unlocks_user_id", "mt_icon_pack_unlocks", ["user_id"])
    op.create_index("ix_mt_icon_pack_unlocks_pack_id", "mt_icon_pack_unlocks", ["pack_id"])


def downgrade() -> None:
    op.drop_index("ix_mt_icon_pack_unlocks_pack_id", table_name="mt_icon_pack_unlocks")
    op.drop_index("ix_mt_icon_pack_unlocks_user_id", table_name="mt_icon_pack_unlocks")
    op.drop_table("mt_icon_pack_unlocks")

    op.drop_index("ix__mt_wallet_ledger__user_created", table_name="mt_wallet_ledger")
    op.drop_index("ix_mt_wallet_ledger_user_id", table_name="mt_wallet_ledger")
    op.drop_table("mt_wallet_ledger")

    op.drop_table("mt_user_wallets")
    op.drop_table("mt_catalog_icon_search_tags")

    op.drop_constraint("fk_mt_icon_packs_cover_icon_id", "mt_icon_packs", type_="foreignkey")
    op.drop_index("ix__mt_catalog_icons__pack_sort", table_name="mt_catalog_icons")
    op.drop_index("uq__mt_catalog_icons__pack_slug", table_name="mt_catalog_icons")
    op.drop_index("ix_mt_catalog_icons_pack_id", table_name="mt_catalog_icons")
    op.drop_table("mt_catalog_icons")

    op.drop_index("ix_mt_icon_packs_author_id", table_name="mt_icon_packs")
    op.drop_table("mt_icon_packs")
    op.drop_table("mt_icon_search_tags")
    op.drop_column("mt_users", "is_staff")
