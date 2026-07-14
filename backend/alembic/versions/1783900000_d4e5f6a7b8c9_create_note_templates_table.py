"""create note templates table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-14 18:45:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_TEMPLATES: tuple[tuple[str, dict[str, str], dict[str, str]], ...] = (
    (
        "daily_reflection",
        {"en": "Daily reflection", "ru": "Дневная рефлексия"},
        {
            "en": (
                "## What I did\n\n"
                "\n"
                "## What got in the way\n\n"
                "\n"
                "## What I'll do tomorrow\n\n"
            ),
            "ru": (
                "## Что я делал\n\n"
                "\n"
                "## Что мне мешало\n\n"
                "\n"
                "## Что я буду делать завтра\n\n"
            ),
        },
    ),
    (
        "gratitude",
        {"en": "Gratitude", "ru": "Благодарность"},
        {
            "en": (
                "## Three things I'm grateful for\n\n"
                "1. \n"
                "2. \n"
                "3. \n"
            ),
            "ru": (
                "## Три вещи, за которые я благодарен\n\n"
                "1. \n"
                "2. \n"
                "3. \n"
            ),
        },
    ),
    (
        "mood_check_in",
        {"en": "Mood check-in", "ru": "Чек-ин настроения"},
        {
            "en": (
                "## How I feel\n\n"
                "\n"
                "## Why\n\n"
                "\n"
                "## What would help\n\n"
            ),
            "ru": (
                "## Как я себя чувствую\n\n"
                "\n"
                "## Почему\n\n"
                "\n"
                "## Что бы помогло\n\n"
            ),
        },
    ),
)


def upgrade() -> None:
    op.create_table(
        "mt_note_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bodies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_note_templates__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_note_templates")),
        sa.UniqueConstraint("user_id", "slug", name=op.f("uq__mt_note_templates__user_id_slug")),
    )
    op.create_index(
        op.f("ix__mt_note_templates__user_id"),
        "mt_note_templates",
        ["user_id"],
        unique=False,
    )

    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM mt_users")).fetchall()
    insert_stmt = sa.text(
        """
        INSERT INTO mt_note_templates (user_id, slug, labels, bodies, sort_order)
        VALUES (
            :user_id,
            :slug,
            CAST(:labels AS jsonb),
            CAST(:bodies AS jsonb),
            :sort_order
        )
        """
    )

    for (user_id,) in users:
        for sort_order, (slug, labels, bodies) in enumerate(_DEFAULT_TEMPLATES):
            conn.execute(
                insert_stmt,
                {
                    "user_id": user_id,
                    "slug": slug,
                    "labels": json.dumps(labels, ensure_ascii=False),
                    "bodies": json.dumps(bodies, ensure_ascii=False),
                    "sort_order": sort_order,
                },
            )


def downgrade() -> None:
    op.drop_index(op.f("ix__mt_note_templates__user_id"), table_name="mt_note_templates")
    op.drop_table("mt_note_templates")
