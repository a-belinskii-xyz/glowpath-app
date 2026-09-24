import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.default_goals import DEFAULT_GOALS
from app.core.default_note_templates import DEFAULT_NOTE_TEMPLATES
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS, DEFAULT_TAG_ICON_TYPE
from app.core.onboarding_packs import ComposedDefaults, PackNoteTemplate, PackTagGroup
from app.models.goal import Goal
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.models.user import User
from app.models.user_mood_preferences import UserMoodPreferences
from app.models.user_notification_schedule import UserNotificationSchedule
from app.schemas.notification_settings import DEFAULT_TIME_BY_KIND, PROVISIONED_KINDS
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
                color=default_goal.color,
                icon_type="emoji",
                icon=default_goal.icon,
            )
        )


def provision_composed_defaults(
    db: Session,
    user_id: uuid.UUID,
    composed: ComposedDefaults,
    *,
    starts_on: date,
    include_goals: bool = True,
    update_existing_visibility: bool = True,
) -> None:
    """Idempotently create tag groups/tags/templates/goals from composed packs."""
    existing_groups = {
        group.slug: group
        for group in db.scalars(select(TagGroup).where(TagGroup.user_id == user_id)).all()
    }
    existing_templates = set(
        db.scalars(select(NoteTemplate.slug).where(NoteTemplate.user_id == user_id)).all()
    )
    existing_goals = set(db.scalars(select(Goal.slug).where(Goal.user_id == user_id)).all())

    visible_limit = settings.entry_visible_tag_group_limit
    visible_count = sum(1 for group in existing_groups.values() if group.show_on_entry)

    for group_def in composed.tag_groups:
        group = existing_groups.get(group_def.slug)
        if group is None:
            show_on_entry = group_def.show_on_entry
            if not update_existing_visibility:
                show_on_entry = visible_count < visible_limit
            group = _create_tag_group(
                db,
                user_id,
                group_def,
                show_on_entry=show_on_entry,
                sort_order=group_def.sort_order,
            )
            existing_groups[group.slug] = group
            if show_on_entry:
                visible_count += 1
        elif update_existing_visibility:
            group.show_on_entry = group_def.show_on_entry
            group.sort_order = group_def.sort_order
            group.labels = dict(group_def.labels)

        existing_tag_slugs = {
            tag.slug for tag in db.scalars(select(Tag).where(Tag.group_id == group.id)).all()
        }
        for tag_def in group_def.tags:
            if tag_def.slug in existing_tag_slugs:
                continue
            db.add(
                Tag(
                    group_id=group.id,
                    user_id=user_id,
                    slug=tag_def.slug,
                    labels=dict(tag_def.labels),
                    sort_order=tag_def.sort_order,
                    color=tag_def.color,
                    icon_type=tag_def.icon_type,
                    icon=tag_def.icon,
                )
            )

    for template_def in composed.note_templates:
        if template_def.slug in existing_templates:
            continue
        _create_note_template(db, user_id, template_def)
        existing_templates.add(template_def.slug)

    if include_goals:
        goal_visible_limit = settings.entry_visible_goal_limit
        goal_stats_limit = settings.stats_visible_goal_limit
        for order, goal_def in enumerate(composed.goals):
            if goal_def.slug in existing_goals:
                continue
            db.add(
                Goal(
                    user_id=user_id,
                    slug=goal_def.slug,
                    labels=dict(goal_def.labels),
                    times_per_week=goal_def.times_per_week,
                    starts_on=starts_on,
                    sort_order=order,
                    show_on_entry=order < goal_visible_limit,
                    show_in_stats=order < goal_stats_limit,
                    color=goal_def.color,
                    icon_type=goal_def.icon_type,
                    icon=goal_def.icon,
                )
            )
            existing_goals.add(goal_def.slug)

    if update_existing_visibility:
        _sync_tag_group_visibility(db, user_id, composed.tag_groups)


def _create_tag_group(
    db: Session,
    user_id: uuid.UUID,
    group_def: PackTagGroup,
    *,
    show_on_entry: bool | None = None,
    sort_order: int | None = None,
) -> TagGroup:
    group = TagGroup(
        user_id=user_id,
        slug=group_def.slug,
        labels=dict(group_def.labels),
        sort_order=group_def.sort_order if sort_order is None else sort_order,
        show_on_entry=group_def.show_on_entry if show_on_entry is None else show_on_entry,
    )
    db.add(group)
    db.flush()
    return group


def _create_note_template(
    db: Session, user_id: uuid.UUID, template_def: PackNoteTemplate
) -> NoteTemplate:
    template = NoteTemplate(
        user_id=user_id,
        slug=template_def.slug,
        labels=dict(template_def.labels),
        bodies=dict(template_def.bodies),
        sort_order=template_def.sort_order,
    )
    db.add(template)
    return template


def _sync_tag_group_visibility(
    db: Session,
    user_id: uuid.UUID,
    composed_groups: tuple[PackTagGroup, ...],
) -> None:
    visibility = {group.slug: group.show_on_entry for group in composed_groups}
    sort_orders = {group.slug: group.sort_order for group in composed_groups}
    for group in db.scalars(select(TagGroup).where(TagGroup.user_id == user_id)).all():
        if group.slug not in visibility:
            continue
        group.show_on_entry = visibility[group.slug]
        group.sort_order = sort_orders[group.slug]


def provision_notification_settings(db: Session, user_id: uuid.UUID) -> None:
    existing = set(
        db.scalars(
            select(UserNotificationSchedule.kind).where(UserNotificationSchedule.user_id == user_id)
        ).all()
    )
    channels = _default_notification_channels(db, user_id)
    for kind in PROVISIONED_KINDS:
        if kind.value in existing:
            continue
        db.add(
            UserNotificationSchedule(
                user_id=user_id,
                kind=kind.value,
                enabled=False,
                time_of_day=DEFAULT_TIME_BY_KIND[kind],
                interval_days=1,
                channels=list(channels),
            )
        )


def _default_notification_channels(db: Session, user_id: uuid.UUID) -> list[str]:
    user = db.get(User, user_id)
    if user is not None and user.telegram_linked:
        return [NotificationChannel.TELEGRAM.value]
    return [NotificationChannel.EMAIL.value]


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
        .select_from(UserNotificationSchedule)
        .where(UserNotificationSchedule.user_id == user_id)
    )
    return int(count or 0)


def count_user_mood_preferences(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(UserMoodPreferences)
        .where(UserMoodPreferences.user_id == user_id)
    )
    return int(count or 0)
