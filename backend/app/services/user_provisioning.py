import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.default_note_templates import DEFAULT_NOTE_TEMPLATES
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.tag_group import TagGroup


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


def count_user_tag_groups(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(select(func.count()).select_from(TagGroup).where(TagGroup.user_id == user_id))
    return int(count or 0)


def count_user_note_templates(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count()).select_from(NoteTemplate).where(NoteTemplate.user_id == user_id)
    )
    return int(count or 0)
