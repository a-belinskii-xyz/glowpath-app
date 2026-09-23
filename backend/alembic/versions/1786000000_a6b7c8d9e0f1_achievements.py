"""achievements catalog, progress, icon unlocks, wallet ledger kind

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-21 18:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("descriptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("icon_type", sa.String(length=16), server_default="emoji", nullable=False),
        sa.Column("icon", sa.String(length=64), server_default="🏆", nullable=False),
        sa.Column("criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('getting_started', 'streaks', 'collection', 'secrets')",
            name="achievement_category_values",
        ),
        sa.CheckConstraint(
            "visibility IN ('visible', 'secret')",
            name="achievement_visibility_values",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="achievement_status_values",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "mt_achievement_rewards",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("achievement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("catalog_icon_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('tokens', 'icon_pack', 'catalog_icon')",
            name="achievement_reward_kind_values",
        ),
        sa.CheckConstraint(
            "("
            "kind = 'tokens' AND amount IS NOT NULL AND amount > 0 "
            "AND pack_id IS NULL AND catalog_icon_id IS NULL"
            ") OR ("
            "kind = 'icon_pack' AND pack_id IS NOT NULL AND amount IS NULL "
            "AND catalog_icon_id IS NULL"
            ") OR ("
            "kind = 'catalog_icon' AND catalog_icon_id IS NOT NULL "
            "AND amount IS NULL AND pack_id IS NULL"
            ")",
            name="achievement_reward_fields",
        ),
        sa.ForeignKeyConstraint(["achievement_id"], ["mt_achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["mt_icon_packs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["catalog_icon_id"], ["mt_catalog_icons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mt_achievement_rewards_achievement_id",
        "mt_achievement_rewards",
        ["achievement_id"],
    )

    op.create_table(
        "mt_user_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("achievement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress_current", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("progress_target", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewards_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("progress_current >= 0", name="user_achievement_progress_current_non_negative"),
        sa.CheckConstraint("progress_target >= 1", name="user_achievement_progress_target_positive"),
        sa.ForeignKeyConstraint(["achievement_id"], ["mt_achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "achievement_id",
            name="uq__mt_user_achievements__user_achievement",
        ),
    )
    op.create_index("ix_mt_user_achievements_user_id", "mt_user_achievements", ["user_id"])
    op.create_index(
        "ix_mt_user_achievements_achievement_id",
        "mt_user_achievements",
        ["achievement_id"],
    )

    op.create_table(
        "mt_user_catalog_icon_unlocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_icon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["catalog_icon_id"], ["mt_catalog_icons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "catalog_icon_id",
            name="uq__mt_user_catalog_icon_unlocks__user_icon",
        ),
    )
    op.create_index(
        "ix_mt_user_catalog_icon_unlocks_user_id",
        "mt_user_catalog_icon_unlocks",
        ["user_id"],
    )
    op.create_index(
        "ix_mt_user_catalog_icon_unlocks_catalog_icon_id",
        "mt_user_catalog_icon_unlocks",
        ["catalog_icon_id"],
    )

    op.drop_constraint("wallet_ledger_kind_values", "mt_wallet_ledger", type_="check")
    op.create_check_constraint(
        "wallet_ledger_kind_values",
        "mt_wallet_ledger",
        "kind IN ('grant', 'unlock_pack', 'adjustment', 'refund', 'achievement')",
    )
    op.add_column(
        "mt_wallet_ledger",
        sa.Column("achievement_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_mt_wallet_ledger_achievement_id",
        "mt_wallet_ledger",
        "mt_achievements",
        ["achievement_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_mt_wallet_ledger_achievement_id", "mt_wallet_ledger", type_="foreignkey")
    op.drop_column("mt_wallet_ledger", "achievement_id")
    op.drop_constraint("wallet_ledger_kind_values", "mt_wallet_ledger", type_="check")
    op.create_check_constraint(
        "wallet_ledger_kind_values",
        "mt_wallet_ledger",
        "kind IN ('grant', 'unlock_pack', 'adjustment', 'refund')",
    )

    op.drop_index(
        "ix_mt_user_catalog_icon_unlocks_catalog_icon_id",
        table_name="mt_user_catalog_icon_unlocks",
    )
    op.drop_index(
        "ix_mt_user_catalog_icon_unlocks_user_id",
        table_name="mt_user_catalog_icon_unlocks",
    )
    op.drop_table("mt_user_catalog_icon_unlocks")

    op.drop_index("ix_mt_user_achievements_achievement_id", table_name="mt_user_achievements")
    op.drop_index("ix_mt_user_achievements_user_id", table_name="mt_user_achievements")
    op.drop_table("mt_user_achievements")

    op.drop_index("ix_mt_achievement_rewards_achievement_id", table_name="mt_achievement_rewards")
    op.drop_table("mt_achievement_rewards")
    op.drop_table("mt_achievements")
