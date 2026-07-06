from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.tag import Tag
from app.services.user_provisioning import count_user_tag_groups
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService


def _register(auth_client: TestClient, mailer: FakeEmailService, email: str) -> None:
    response = auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert response.status_code == 201
    assert len(mailer.outbox) == 1


def test_register_creates_default_tags(
    auth_client: TestClient,
    db: Session,
    mailer: FakeEmailService,
) -> None:
    email = "register-tags@example.com"
    _register(auth_client, mailer, email)

    from app.models.user import User

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    assert count_user_tag_groups(db, user.id) == len(DEFAULT_TAG_GROUPS)

    tag_count = db.scalar(select(func.count()).select_from(Tag).where(Tag.user_id == user.id))
    assert tag_count == sum(len(group.tags) for group in DEFAULT_TAG_GROUPS)


def test_register_duplicate_email_returns_409(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    email = "duplicate@example.com"
    _register(auth_client, mailer, email)
    response = auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "password_confirm": "password123"},
    )
    assert response.status_code == 409
