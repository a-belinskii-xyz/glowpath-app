"""notification schedules and worker heartbeats

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-09-24 13:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mt_system_worker_heartbeats",
        sa.Column("worker_name", sa.String(length=64), nullable=False),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("worker_name"),
    )
    op.create_table(
        "mt_user_notification_schedules",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("time_of_day", sa.String(length=5), nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("days_of_week", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column(
            "channels",
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("ARRAY['telegram']::varchar[]"),
            nullable=False,
        ),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "kind",
            name="uq__mt_user_notification_schedules__user_id_kind",
        ),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO mt_user_notification_schedules (
                user_id, kind, enabled, time_of_day, interval_days, days_of_week,
                channels, last_sent_at, created_at, updated_at
            )
            SELECT
                user_id,
                'daily_mood',
                enabled AND daily_mood_reminder_enabled,
                COALESCE(to_char(daily_mood_reminder_time, 'HH24:MI'), '21:00'),
                1,
                NULL::integer[],
                COALESCE(
                    (
                        SELECT array_agg(value)::varchar[]
                        FROM jsonb_array_elements_text(channels) AS value
                    ),
                    ARRAY['email']::varchar[]
                ),
                last_daily_mood_reminder_on::timestamptz,
                created_at,
                updated_at
            FROM mt_user_notification_settings
            UNION ALL
            SELECT
                user_id,
                'goal_tracking',
                enabled AND goal_reminders_enabled,
                COALESCE(to_char(daily_mood_reminder_time, 'HH24:MI'), '12:00'),
                1,
                NULL::integer[],
                COALESCE(
                    (
                        SELECT array_agg(value)::varchar[]
                        FROM jsonb_array_elements_text(channels) AS value
                    ),
                    ARRAY['email']::varchar[]
                ),
                last_goal_reminder_on::timestamptz,
                created_at,
                updated_at
            FROM mt_user_notification_settings
            """
        )
    )
    op.drop_table("mt_user_notification_settings")


def downgrade() -> None:
    op.create_table(
        "mt_user_notification_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "channels",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[\"email\"]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "daily_mood_reminder_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("daily_mood_reminder_time", sa.Time(), nullable=True),
        sa.Column(
            "goal_reminders_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_daily_mood_reminder_on", sa.Date(), nullable=True),
        sa.Column("last_goal_reminder_on", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["mt_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO mt_user_notification_settings (
                user_id, enabled, channels,
                daily_mood_reminder_enabled, daily_mood_reminder_time,
                goal_reminders_enabled,
                last_daily_mood_reminder_on, last_goal_reminder_on,
                created_at, updated_at
            )
            SELECT
                user_id,
                bool_or(enabled),
                COALESCE(
                    (
                        SELECT jsonb_agg(channel)
                        FROM (
                            SELECT DISTINCT unnest(channels) AS channel
                            FROM mt_user_notification_schedules AS inner_row
                            WHERE inner_row.user_id = outer_row.user_id
                        ) AS channel_rows
                    ),
                    '["email"]'::jsonb
                ),
                bool_or(enabled) FILTER (WHERE kind = 'daily_mood'),
                MAX(time_of_day::time) FILTER (WHERE kind = 'daily_mood'),
                bool_or(enabled) FILTER (WHERE kind = 'goal_tracking'),
                MAX(last_sent_at)::date FILTER (WHERE kind = 'daily_mood'),
                MAX(last_sent_at)::date FILTER (WHERE kind = 'goal_tracking'),
                MIN(created_at),
                MAX(updated_at)
            FROM mt_user_notification_schedules AS outer_row
            GROUP BY user_id
            """
        )
    )
    op.drop_table("mt_user_notification_schedules")
    op.drop_table("mt_system_worker_heartbeats")
