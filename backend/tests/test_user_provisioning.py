import uuid

from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.tag import Tag
from app.models.user import User
from app.services.user_provisioning import count_user_tag_groups, provision_default_tags
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
