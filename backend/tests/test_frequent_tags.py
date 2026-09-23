from datetime import UTC, datetime, timedelta

from app.config import settings
from app.models.tag import Tag
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _enable_frequent_tags(
    monkeypatch,
    *,
    enabled: bool = True,
    percent: int = 100,
    emails: str = "",
    user_ids: str = "",
    limit: int = 8,
    days: int = 7,
) -> None:
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags", enabled)
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags_percent", percent)
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags_emails", emails)
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags_user_ids", user_ids)
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags_limit", limit)
    monkeypatch.setattr(settings, "feature_weekly_frequent_tags_days", days)


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


def test_frequent_tags_default_off(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "freq-off@example.com")
    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["frequent_tags_enabled"] is False
    assert body["frequent_tags"] == []

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json()["features"]["weekly_frequent_tags"] is False


def test_frequent_tags_ranked_and_windowed(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch,
) -> None:
    _enable_frequent_tags(monkeypatch, limit=2)
    email = "freq-rank@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    tags = _user_tags(db, email)
    hot, warm, old = tags[0], tags[1], tags[2]

    for _ in range(3):
        _create_entry(auth_client, token, tag_ids=[str(hot.id)], recorded_at=_iso_days_ago(1))
    _create_entry(auth_client, token, tag_ids=[str(warm.id)], recorded_at=_iso_days_ago(2))
    for _ in range(5):
        _create_entry(auth_client, token, tag_ids=[str(old.id)], recorded_at=_iso_days_ago(20))

    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["frequent_tags_enabled"] is True
    frequent_ids = [item["id"] for item in body["frequent_tags"]]
    assert frequent_ids == [str(hot.id), str(warm.id)]
    assert str(old.id) not in frequent_ids


def test_frequent_tags_email_allowlist(
    auth_client: TestClient,
    mailer: FakeEmailService,
    monkeypatch,
) -> None:
    _enable_frequent_tags(monkeypatch, percent=0, emails="freq-in@example.com")
    in_token = register_verify_and_login(auth_client, mailer, "freq-in@example.com")
    out_token = register_verify_and_login(auth_client, mailer, "freq-out@example.com")

    enabled = auth_client.get("/v1/tag-groups", headers=_auth_headers(in_token))
    disabled = auth_client.get("/v1/tag-groups", headers=_auth_headers(out_token))
    assert enabled.json()["frequent_tags_enabled"] is True
    assert disabled.json()["frequent_tags_enabled"] is False
    assert (
        auth_client.get("/v1/auth/me", headers=_auth_headers(in_token)).json()["features"][
            "weekly_frequent_tags"
        ]
        is True
    )
