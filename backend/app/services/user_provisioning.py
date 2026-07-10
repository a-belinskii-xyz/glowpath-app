import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
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


def count_user_tag_groups(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(select(func.count()).select_from(TagGroup).where(TagGroup.user_id == user_id))
    return int(count or 0)
