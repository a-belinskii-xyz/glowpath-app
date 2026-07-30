"""widen photo position range for reorder

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-07-30 13:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck__mt_mood_entry_attachments__kind_position"),
        "mt_mood_entry_attachments",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck__mt_mood_entry_attachments__kind_position"),
        "mt_mood_entry_attachments",
        "(kind = 'photo' AND position BETWEEN 1 AND 10) OR "
        "(kind = 'audio' AND position IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck__mt_mood_entry_attachments__kind_position"),
        "mt_mood_entry_attachments",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck__mt_mood_entry_attachments__kind_position"),
        "mt_mood_entry_attachments",
        "(kind = 'photo' AND position BETWEEN 1 AND 5) OR "
        "(kind = 'audio' AND position IS NULL)",
    )
