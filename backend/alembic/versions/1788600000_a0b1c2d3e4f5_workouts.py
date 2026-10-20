"""exercises, workout sets and the workouts toggle

Revision ID: a0b1c2d3e4f5
Revises: z0a1b2c3d4e5
Create Date: 2026-10-20 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: str | Sequence[str] | None = "z0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mt_body_settings",
        sa.Column("show_workouts", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "mt_exercises",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("with_weight", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            name=op.f("fk__mt_exercises__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_exercises")),
        sa.UniqueConstraint("user_id", "name", name=op.f("uq__mt_exercises__user_id_name")),
    )
    op.create_index(op.f("ix__mt_exercises__user_id"), "mt_exercises", ["user_id"], unique=False)
    op.create_table(
        "mt_workout_sets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("reps > 0", name=op.f("ck__mt_workout_sets__workout_set_reps_positive")),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name=op.f("ck__mt_workout_sets__workout_set_weight_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["mt_exercises.id"],
            name=op.f("fk__mt_workout_sets__exercise_id__mt_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["mt_users.id"],
            name=op.f("fk__mt_workout_sets__user_id__mt_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk__mt_workout_sets")),
    )
    op.create_index(
        op.f("ix__mt_workout_sets__exercise_id"), "mt_workout_sets", ["exercise_id"], unique=False
    )
    op.create_index(
        op.f("ix__mt_workout_sets__user_id"), "mt_workout_sets", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix__mt_workout_sets__user_id"), table_name="mt_workout_sets")
    op.drop_index(op.f("ix__mt_workout_sets__exercise_id"), table_name="mt_workout_sets")
    op.drop_table("mt_workout_sets")
    op.drop_index(op.f("ix__mt_exercises__user_id"), table_name="mt_exercises")
    op.drop_table("mt_exercises")
    op.drop_column("mt_body_settings", "show_workouts")
