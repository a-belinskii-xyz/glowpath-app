"""diary restores from export archives

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-10-01 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, Sequence[str], None] = "j4k5l6m7n8o9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MARKED_TABLES = ("mt_mood_entries", "mt_tag_groups", "mt_tags", "mt_goals", "mt_note_templates")


def upgrade() -> None:
    op.create_table(
        "mt_diary_restores",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("archive_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archive", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "stored_files",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('preview', 'applied', 'cancelled')",
            name=op.f("ck__mt_diary_restores__diary_restore_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_diary_restores__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_diary_restores")),
    )
    op.create_index(
        "ix__mt_diary_restores__user_id__status",
        "mt_diary_restores",
        ["user_id", "status"],
        unique=False,
    )

    for table in _MARKED_TABLES:
        op.add_column(table, sa.Column("restore_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk__{table}__restore_id__mt_diary_restores"),
            table,
            "mt_diary_restores",
            ["restore_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.add_column("mt_mood_entries", sa.Column("origin_id", sa.UUID(), nullable=True))
    op.create_index(
        "ix__mt_mood_entries__user_id__origin_id",
        "mt_mood_entries",
        ["user_id", "origin_id"],
        unique=False,
        postgresql_where=sa.text("origin_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix__mt_mood_entries__user_id__origin_id",
        table_name="mt_mood_entries",
        postgresql_where=sa.text("origin_id IS NOT NULL"),
    )
    op.drop_column("mt_mood_entries", "origin_id")
    for table in reversed(_MARKED_TABLES):
        op.drop_constraint(
            op.f(f"fk__{table}__restore_id__mt_diary_restores"), table, type_="foreignkey"
        )
        op.drop_column(table, "restore_id")
    op.drop_index("ix__mt_diary_restores__user_id__status", table_name="mt_diary_restores")
    op.drop_table("mt_diary_restores")
