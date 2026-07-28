"""add tag icons and style

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-24 15:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KNOWN_TAG_STYLES: dict[str, tuple[str, str]] = {
    "sunny": ("#f59e0b", "☀️"),
    "cloudy": ("#94a3b8", "☁️"),
    "rain": ("#60a5fa", "🌧"),
    "thunderstorm": ("#6366f1", "⛈"),
    "slept_well": ("#34d399", "😴"),
    "average_sleep": ("#94a3b8", "😑"),
    "slept_poorly": ("#f87171", "😩"),
    "joy": ("#f59e0b", "😊"),
    "anxiety": ("#a78bfa", "😰"),
    "fatigue": ("#94a3b8", "😮‍💨"),
    "calm": ("#34d399", "😌"),
    "work": ("#60a5fa", "💼"),
    "sport": ("#34d399", "🏃"),
    "social": ("#f472b6", "💬"),
    "rest": ("#a78bfa", "🛋"),
    "running": ("#34d399", "🏃"),
    "reading": ("#60a5fa", "📖"),
    "cooking": ("#f59e0b", "🍳"),
    "family": ("#f472b6", "👨‍👩‍👧"),
    "friends": ("#60a5fa", "👥"),
    "colleagues": ("#94a3b8", "🧑‍💼"),
    "home": ("#f59e0b", "🏠"),
    "office": ("#60a5fa", "🏢"),
    "cafe": ("#d97706", "☕"),
    "outdoors": ("#34d399", "🌳"),
}


def upgrade() -> None:
    op.add_column(
        "mt_tags",
        sa.Column("color", sa.String(length=7), server_default="#94a3b8", nullable=False),
    )
    op.add_column(
        "mt_tags",
        sa.Column("icon_type", sa.String(length=16), server_default="emoji", nullable=False),
    )
    op.add_column(
        "mt_tags",
        sa.Column("icon", sa.String(length=64), server_default="🏷", nullable=False),
    )

    bind = op.get_bind()
    for slug, (color, icon) in _KNOWN_TAG_STYLES.items():
        bind.execute(
            sa.text(
                "UPDATE mt_tags SET color = :color, icon_type = 'emoji', icon = :icon "
                "WHERE slug = :slug"
            ),
            {"color": color, "icon": icon, "slug": slug},
        )

    op.create_table(
        "mt_user_tag_icons",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
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
        sa.ForeignKeyConstraint(["tag_id"], ["mt_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix__mt_user_tag_icons__user_tag",
        "mt_user_tag_icons",
        ["user_id", "tag_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mt_user_tag_icons_user_id"),
        "mt_user_tag_icons",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mt_user_tag_icons_tag_id"),
        "mt_user_tag_icons",
        ["tag_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_mt_user_tag_icons_tag_id"), table_name="mt_user_tag_icons")
    op.drop_index(op.f("ix_mt_user_tag_icons_user_id"), table_name="mt_user_tag_icons")
    op.drop_index("ix__mt_user_tag_icons__user_tag", table_name="mt_user_tag_icons")
    op.drop_table("mt_user_tag_icons")
    op.drop_column("mt_tags", "icon")
    op.drop_column("mt_tags", "icon_type")
    op.drop_column("mt_tags", "color")
