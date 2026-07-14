import uuid

from app.core.default_note_templates import DEFAULT_NOTE_TEMPLATES
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.note_template import NoteTemplate
from app.models.tag import Tag
from app.models.user import User
from app.services.user_provisioning import (
    count_user_note_templates,
    count_user_tag_groups,
    provision_default_note_templates,
    provision_default_tags,
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
