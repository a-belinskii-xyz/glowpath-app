import uuid
from datetime import UTC, date, datetime

from app.core.default_goals import DEFAULT_GOALS
from app.core.default_note_templates import DEFAULT_NOTE_TEMPLATES
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.goal import Goal
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.user_provisioning import (
    count_user_goals,
    count_user_mood_preferences,
    count_user_note_templates,
    count_user_notification_settings,
    count_user_tag_groups,
    provision_default_goals,
    provision_default_note_templates,
    provision_default_tags,
    provision_mood_preferences,
    provision_notification_settings,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_provision_default_tags_creates_groups_and_tags(db: Session) -> None:
    user = User(email=f"provision-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    provision_default_tags(db, user.id)
    db.flush()

    group_count = count_user_tag_groups(db, user.id)
    tag_count = db.scalar(select(func.count()).select_from(Tag).where(Tag.user_id == user.id))

    assert group_count == len(DEFAULT_TAG_GROUPS)
    assert tag_count == sum(len(group.tags) for group in DEFAULT_TAG_GROUPS)


def test_provision_default_note_templates(db: Session) -> None:
    user = User(email=f"templates-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    provision_default_note_templates(db, user.id)
    db.flush()

    template_count = count_user_note_templates(db, user.id)
    slugs = list(
        db.scalars(
            select(NoteTemplate.slug)
            .where(NoteTemplate.user_id == user.id)
            .order_by(NoteTemplate.sort_order)
        ).all()
    )

    assert template_count == len(DEFAULT_NOTE_TEMPLATES)
    assert slugs == [item.slug for item in DEFAULT_NOTE_TEMPLATES]


def test_provision_default_goals(db: Session) -> None:
    user = User(email=f"goals-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    starts_on = date(2026, 7, 15)
    provision_default_goals(db, user.id, starts_on=starts_on)
    db.flush()

    assert count_user_goals(db, user.id) == len(DEFAULT_GOALS)
    goals = list(
        db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.sort_order)).all()
    )
    assert [goal.slug for goal in goals] == [item.slug for item in DEFAULT_GOALS]
    assert all(goal.starts_on == starts_on for goal in goals)
    assert sum(1 for goal in goals if goal.show_on_entry) == 3
    assert sum(1 for goal in goals if goal.show_in_stats) == len(DEFAULT_GOALS)


def test_provision_notification_settings(db: Session) -> None:
    user = User(email=f"notify-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    provision_notification_settings(db, user.id)
    db.flush()

    assert count_user_notification_settings(db, user.id) == 2
    prefs = db.scalars(
        select(UserNotificationSchedule).where(UserNotificationSchedule.user_id == user.id)
    ).all()
    assert {row.kind for row in prefs} == {"daily_mood", "goal_tracking"}
    assert all(row.channels == ["email"] for row in prefs)


def test_provision_notification_settings_telegram_native(db: Session) -> None:
    user = User(
        email=None,
        telegram_user_id=701,
        telegram_chat_id=701,
        telegram_linked_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()

    provision_notification_settings(db, user.id)
    db.flush()

    prefs = db.scalars(
        select(UserNotificationSchedule).where(UserNotificationSchedule.user_id == user.id)
    ).all()
    assert prefs
    assert all(row.channels == ["telegram"] for row in prefs)


def test_provision_mood_preferences(db: Session) -> None:
    user = User(email=f"mood-prefs-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    provision_mood_preferences(db, user.id)
    db.flush()

    assert count_user_mood_preferences(db, user.id) == 1
