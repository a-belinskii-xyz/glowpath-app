from unittest.mock import patch

from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.tag import Tag
from app.models.user import User
from app.services.auth_service import GoogleProfile
from app.services.user_provisioning import count_user_tag_groups
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@patch("app.api.v1.auth.verify_google_id_token")
def test_google_id_token_creates_user_and_tags(
    mock_verify: object,
    auth_client: TestClient,
    db: Session,
) -> None:
    mock_verify.return_value = GoogleProfile(
        sub="google-sub-1",
        email="google-new@example.com",
        email_verified=True,
    )

    response = auth_client.post("/v1/auth/google", json={"id_token": "fake-token"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    user = db.scalar(select(User).where(User.email == "google-new@example.com"))
    assert user is not None
    assert user.google_sub == "google-sub-1"
    assert count_user_tag_groups(db, user.id) == len(DEFAULT_TAG_GROUPS)
    tag_count = db.scalar(select(func.count()).select_from(Tag).where(Tag.user_id == user.id))
    assert tag_count == sum(len(group.tags) for group in DEFAULT_TAG_GROUPS)


@patch("app.api.v1.auth.verify_google_id_token")
def test_google_id_token_links_existing_email_account(
    mock_verify: object,
    auth_client: TestClient,
    db: Session,
) -> None:
    email = "link-google@example.com"
    auth_client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123"},
    )

    mock_verify.return_value = GoogleProfile(
        sub="google-sub-link",
        email=email,
        email_verified=True,
    )
    response = auth_client.post("/v1/auth/google", json={"id_token": "fake-token"})
    assert response.status_code == 200

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.google_sub == "google-sub-link"
