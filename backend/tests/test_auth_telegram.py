from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.config import settings
from app.core.default_tag_groups import DEFAULT_TAG_GROUPS
from app.models.user import User
from app.services.user_provisioning import count_user_tag_groups
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.test_telegram_init_data import BOT_TOKEN, build_init_data


def test_telegram_auth_creates_user_without_email(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", BOT_TOKEN)
    telegram_user_id = 900_001
    init_data = build_init_data(
        user={"id": telegram_user_id, "first_name": "Mila", "language_code": "ru"},
    )

    response = auth_client.post(
        "/v1/auth/telegram",
        json={"init_data": init_data, "timezone": "Europe/Minsk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_created"] is True
    token = body["access_token"]

    me = auth_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    profile = me.json()
    assert profile["email"] is None
    assert profile["email_verified"] is False
    assert profile["telegram_linked"] is True
    assert profile["can_unlink_telegram"] is False
    assert profile["has_password"] is False

    user = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    assert user is not None
    assert user.email is None
    assert user.telegram_chat_id == telegram_user_id
    assert count_user_tag_groups(db, user.id) == len(DEFAULT_TAG_GROUPS)

    entries = auth_client.get(
        "/v1/mood-entries",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert entries.status_code == 200

    refresh = auth_client.post(
        "/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh.status_code == 200


def test_telegram_auth_logs_in_existing_linked_user(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", BOT_TOKEN)
    telegram_user_id = 900_002
    existing = User(
        email=f"linked-{uuid.uuid4()}@example.com",
        password_hash="x",
        email_verified_at=datetime.now(UTC),
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_user_id,
        telegram_linked_at=datetime.now(UTC),
    )
    db.add(existing)
    db.flush()

    init_data = build_init_data(user={"id": telegram_user_id, "first_name": "Ada"})
    response = auth_client.post("/v1/auth/telegram", json={"init_data": init_data})
    assert response.status_code == 200
    assert response.json().get("user_created") in (None, False)

    me = auth_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == existing.email
    assert me.json()["can_unlink_telegram"] is True


def test_telegram_auth_rejects_invalid_hash(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", BOT_TOKEN)
    init_data = build_init_data(
        user={"id": 1, "first_name": "Ada"},
        hash_override="0" * 64,
    )
    response = auth_client.post("/v1/auth/telegram", json={"init_data": init_data})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_telegram_init_data"


def test_telegram_auth_requires_bot_token(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "")
    init_data = build_init_data(user={"id": 1, "first_name": "Ada"})
    response = auth_client.post("/v1/auth/telegram", json={"init_data": init_data})
    assert response.status_code == 503


def test_telegram_only_user_cannot_unlink(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(settings, "telegram_bot_username", "glowpath_bot")
    monkeypatch.setattr(settings, "telegram_bot_service_token", "test-service-token")
    init_data = build_init_data(user={"id": 900_003, "first_name": "Solo"})
    login = auth_client.post("/v1/auth/telegram", json={"init_data": init_data})
    token = login.json()["access_token"]

    unlink = auth_client.delete(
        "/v1/telegram/link",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unlink.status_code == 409
    assert unlink.json()["detail"]["code"] == "telegram_unlink_not_allowed"
