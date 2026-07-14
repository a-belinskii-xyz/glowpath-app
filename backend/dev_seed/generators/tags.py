from __future__ import annotations

import uuid

from app.models.tag import Tag
from app.models.tag_group import TagGroup
from app.services.user_provisioning import provision_default_tags
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dev_seed.personas import Persona
from dev_seed.rng import SeededRNG


def provision_tags(
    db: Session,
    *,
    user_id: uuid.UUID,
    persona: Persona,
    rng: SeededRNG,
) -> list[Tag]:
    """Default catalog + persona custom groups. Returns all tags for the user."""
    provision_default_tags(db, user_id)
    db.flush()

    group_count = db.scalar(
        select(func.count()).select_from(TagGroup).where(TagGroup.user_id == user_id)
    )
    base_order = int(group_count or 0)

    for group_offset, custom_group in enumerate(persona.custom_groups):
        group = TagGroup(
            id=rng.uuid("tag_group", f"{persona.key}:{custom_group.slug}"),
            user_id=user_id,
            slug=custom_group.slug,
            labels=dict(custom_group.labels),
            sort_order=base_order + group_offset,
            show_on_entry=True,
        )
        db.add(group)
        db.flush()
        for tag_order, custom_tag in enumerate(custom_group.tags):
            db.add(
                Tag(
                    id=rng.uuid("tag", f"{persona.key}:{custom_group.slug}:{custom_tag.slug}"),
                    group_id=group.id,
                    user_id=user_id,
                    slug=custom_tag.slug,
                    labels=dict(custom_tag.labels),
                    sort_order=tag_order,
                )
            )
        db.flush()

    return list(db.scalars(select(Tag).where(Tag.user_id == user_id)).all())
