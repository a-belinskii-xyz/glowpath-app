from datetime import UTC, datetime, timedelta

from app.models.tag import Tag
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _iso_days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _create_entry(
    auth_client: TestClient,
    token: str,
    *,
    tag_ids: list[str],
    recorded_at: str,
) -> None:
    response = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 4,
            "recorded_at": recorded_at,
            "tag_ids": tag_ids,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201


def _user_tags(db: Session, email: str, *, limit: int = 3) -> list[Tag]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user.id).limit(limit)).all())
    assert len(tags) >= limit
    return tags


def test_frequent_tags_empty_without_entries(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "freq-empty@example.com")
    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["frequent_tags"] == []
    assert "frequent_tags_enabled" not in body

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert "weekly_frequent_tags" not in me.json()["features"]


def test_frequent_tags_ranked_and_windowed(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    email = "freq-rank@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    tags = _user_tags(db, email)
    hot, warm, old = tags[0], tags[1], tags[2]

    for _ in range(3):
        _create_entry(auth_client, token, tag_ids=[str(hot.id)], recorded_at=_iso_days_ago(1))
    _create_entry(auth_client, token, tag_ids=[str(warm.id)], recorded_at=_iso_days_ago(20))
    for _ in range(5):
        _create_entry(auth_client, token, tag_ids=[str(old.id)], recorded_at=_iso_days_ago(40))

    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert response.status_code == 200
    frequent_ids = [item["id"] for item in response.json()["frequent_tags"]]
    assert frequent_ids == [str(hot.id), str(warm.id)]
    assert str(old.id) not in frequent_ids


def test_frequent_tags_limit(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    email = "freq-limit@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user.id)).all())
    assert len(tags) > 8
    _create_entry(
        auth_client, token, tag_ids=[str(tag.id) for tag in tags], recorded_at=_iso_days_ago(1)
    )

    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert len(response.json()["frequent_tags"]) == 8
