import io
import uuid

import pytest
from app.config import settings
from app.models.mood_entry import MoodEntry
from app.models.tag import Tag
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

SERVICE_HEADER = "X-Telegram-Bot-Service-Token"
TG_USER_ID = 880001


@pytest.fixture
def telegram_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "telegram_bot_username", "mood_tracker_test_bot")
    monkeypatch.setattr(settings, "telegram_bot_service_token", "test-service-token")
    monkeypatch.setattr(settings, "telegram_link_code_expire_minutes", 15)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _service_headers() -> dict[str, str]:
    return {SERVICE_HEADER: "test-service-token"}


def _link_user(
    auth_client: TestClient,
    token: str,
    *,
    telegram_user_id: int = TG_USER_ID,
    locale: str = "en",
) -> None:
    create = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token))
    assert create.status_code == 200
    linked = auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": create.json()["code"],
            "telegram_user_id": telegram_user_id,
            "telegram_chat_id": telegram_user_id,
            "locale": locale,
        },
    )
    assert linked.status_code == 200


def test_bot_catalog_requires_service_token(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-cat-{uuid.uuid4()}@example.com")
    _link_user(auth_client, token)
    response = auth_client.get(
        "/v1/telegram/bot/catalog",
        params={"telegram_user_id": TG_USER_ID},
    )
    assert response.status_code == 401


def test_bot_catalog_404_when_not_linked(
    auth_client: TestClient,
    telegram_configured: None,
) -> None:
    response = auth_client.get(
        "/v1/telegram/bot/catalog",
        headers=_service_headers(),
        params={"telegram_user_id": 999999},
    )
    assert response.status_code == 404


def test_bot_catalog_returns_scores_tags_goals(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-cat2-{uuid.uuid4()}@example.com")
    _link_user(auth_client, token, locale="ru-RU")

    response = auth_client.get(
        "/v1/telegram/bot/catalog",
        headers=_service_headers(),
        params={"telegram_user_id": TG_USER_ID},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "ru"
    assert len(body["scores"]) == 5
    assert body["scores"][0]["score"] == 1
    assert "emoji" in body["scores"][0]
    assert "label" in body["scores"][0]
    assert isinstance(body["tag_groups"], list)
    assert all(group["show_on_entry"] for group in body["tag_groups"])
    assert body["frequent_tags"] == []
    assert isinstance(body["goals"], list)


def test_bot_create_entry_with_source(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    email = f"tg-entry-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    _link_user(auth_client, token)

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user.id).limit(1)).all())
    tag_ids = [str(tags[0].id)] if tags else []

    unauthorized = auth_client.post(
        "/v1/telegram/bot/entries",
        json={
            "telegram_user_id": TG_USER_ID,
            "score": 4,
            "tag_ids": tag_ids,
            "source": "telegram:bot",
        },
    )
    assert unauthorized.status_code == 401

    created = auth_client.post(
        "/v1/telegram/bot/entries",
        headers=_service_headers(),
        json={
            "telegram_user_id": TG_USER_ID,
            "score": 4,
            "tag_ids": tag_ids,
            "note": "from bot",
            "source": "telegram:bot",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["score"] == 4
    assert body["note"] == "from bot"
    assert "source" not in body

    entry = db.scalar(select(MoodEntry).where(MoodEntry.id == body["id"]))
    assert entry is not None
    assert entry.source == "telegram:bot"
    assert entry.user_id == user.id


def test_bot_create_entry_404_when_not_linked(
    auth_client: TestClient,
    telegram_configured: None,
) -> None:
    response = auth_client.post(
        "/v1/telegram/bot/entries",
        headers=_service_headers(),
        json={"telegram_user_id": 111222, "score": 3},
    )
    assert response.status_code == 404


def test_bot_session_crud(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-sess-{uuid.uuid4()}@example.com")
    _link_user(auth_client, token, telegram_user_id=880002)

    empty = auth_client.get(
        "/v1/telegram/bot/sessions/880002",
        headers=_service_headers(),
    )
    assert empty.status_code == 200
    assert empty.json()["state"] == {}

    upsert = auth_client.put(
        "/v1/telegram/bot/sessions/880002",
        headers=_service_headers(),
        json={"state": {"step": "choose_score", "score": None}},
    )
    assert upsert.status_code == 200
    assert upsert.json()["state"]["step"] == "choose_score"

    got = auth_client.get(
        "/v1/telegram/bot/sessions/880002",
        headers=_service_headers(),
    )
    assert got.json()["state"]["step"] == "choose_score"

    deleted = auth_client.delete(
        "/v1/telegram/bot/sessions/880002",
        headers=_service_headers(),
    )
    assert deleted.status_code == 204

    again = auth_client.get(
        "/v1/telegram/bot/sessions/880002",
        headers=_service_headers(),
    )
    assert again.json()["state"] == {}


def test_bot_session_404_when_not_linked(
    auth_client: TestClient,
    telegram_configured: None,
) -> None:
    response = auth_client.get(
        "/v1/telegram/bot/sessions/424200",
        headers=_service_headers(),
    )
    assert response.status_code == 404


def test_bot_upload_attachment(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-att-{uuid.uuid4()}@example.com")
    _link_user(auth_client, token, telegram_user_id=880003)

    created = auth_client.post(
        "/v1/telegram/bot/entries",
        headers=_service_headers(),
        json={"telegram_user_id": 880003, "score": 3, "source": "telegram:bot"},
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    audio = io.BytesIO(b"OggS" + b"\x00" * 64)
    response = auth_client.post(
        f"/v1/telegram/bot/entries/{entry_id}/attachments",
        headers=_service_headers(),
        data={"telegram_user_id": "880003", "kind": "audio"},
        files={"file": ("voice.ogg", audio, "audio/ogg")},
    )
    assert response.status_code == 201
    assert response.json()["kind"] == "audio"
    assert response.json()["mime_type"] == "audio/ogg"
