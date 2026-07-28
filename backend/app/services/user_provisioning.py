import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.default_goals import DEFAULT_GOALS
from app.core.default_note_templates import DEFAULT_NOTE_TEMPLATES
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS, DEFAULT_TAG_ICON_TYPE
from app.models.goal import Goal
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user_mood_preferences import UserMoodPreferences
from app.models.user_notification_settings import UserNotificationSettings
from app.services.notifications.base import NotificationChannel


def provision_default_tags(db: Session, user_id: uuid.UUID) -> None:
    visible_limit = settings.entry_visible_tag_group_limit
    for group_order, default_group in enumerate(DEFAULT_TAG_GROUPS):
        group = TagGroup(
            user_id=user_id,
            slug=default_group.slug,
            labels=dict(default_group.labels),
            sort_order=group_order,
            show_on_entry=group_order < visible_limit,
        )
        db.add(group)
        db.flush()

        for tag_order, default_tag in enumerate(default_group.tags):
            db.add(
                Tag(
                    group_id=group.id,
                    user_id=user_id,
                    slug=default_tag.slug,
                    labels=dict(default_tag.labels),
                    sort_order=tag_order,
                    color=default_tag.color,
                    icon_type=DEFAULT_TAG_ICON_TYPE,
                    icon=default_tag.icon,
                )
            )


def provision_default_note_templates(db: Session, user_id: uuid.UUID) -> None:
    for order, default_template in enumerate(DEFAULT_NOTE_TEMPLATES):
        db.add(
            NoteTemplate(
                user_id=user_id,
                slug=default_template.slug,
                labels=dict(default_template.labels),
                bodies=dict(default_template.bodies),
                sort_order=order,
            )
        )


def provision_default_goals(db: Session, user_id: uuid.UUID, *, starts_on: date) -> None:
    visible_limit = settings.entry_visible_goal_limit
    stats_limit = settings.stats_visible_goal_limit
    for order, default_goal in enumerate(DEFAULT_GOALS):
        db.add(
            Goal(
                user_id=user_id,
                slug=default_goal.slug,
                labels=dict(default_goal.labels),
                times_per_week=default_goal.times_per_week,
                starts_on=starts_on,
                sort_order=order,
                show_on_entry=order < visible_limit,
                show_in_stats=order < stats_limit,
            )
        )


def provision_notification_settings(db: Session, user_id: uuid.UUID) -> None:
    db.add(
        UserNotificationSettings(
            user_id=user_id,
            enabled=False,
            channels=[NotificationChannel.EMAIL.value],
            daily_mood_reminder_enabled=False,
            daily_mood_reminder_time=None,
            goal_reminders_enabled=False,
        )
    )


def provision_mood_preferences(db: Session, user_id: uuid.UUID) -> None:
    db.add(UserMoodPreferences(user_id=user_id, score_styles=None))


def count_user_tag_groups(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(select(func.count()).select_from(TagGroup).where(TagGroup.user_id == user_id))
    return int(count or 0)


def count_user_note_templates(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count()).select_from(NoteTemplate).where(NoteTemplate.user_id == user_id)
    )
    return int(count or 0)


def count_user_goals(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(select(func.count()).select_from(Goal).where(Goal.user_id == user_id))
    return int(count or 0)


def count_user_notification_settings(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(UserNotificationSettings)
        .where(UserNotificationSettings.user_id == user_id)
    )
    return int(count or 0)


def count_user_mood_preferences(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(UserMoodPreferences)
        .where(UserMoodPreferences.user_id == user_id)
    )
    return int(count or 0)
