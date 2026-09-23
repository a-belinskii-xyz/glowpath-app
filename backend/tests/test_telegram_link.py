import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.core.security import hash_token
from app.models.telegram_link_code import TelegramLinkCode
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

SERVICE_HEADER = "X-Telegram-Bot-Service-Token"


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


def test_telegram_entry_point_is_public(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_username", "glowpath_bot")
    response = client.get("/v1/telegram/entry-point")
    assert response.status_code == 200
    assert response.json() == {
        "bot_username": "glowpath_bot",
        "bot_url": "https://t.me/glowpath_bot",
    }


def test_get_link_status_unlinked(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-{uuid.uuid4()}@example.com")
    response = auth_client.get("/v1/telegram/link", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["linked"] is False
    assert body["bot_configured"] is True
    assert body["bot_username"] == "mood_tracker_test_bot"


def test_create_link_code_requires_bot_config(
    auth_client: TestClient,
    mailer: FakeEmailService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "")
    monkeypatch.setattr(settings, "telegram_bot_username", "")
    token = register_verify_and_login(auth_client, mailer, f"tg-{uuid.uuid4()}@example.com")
    response = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token))
    assert response.status_code == 503


def test_link_and_unlink_flow(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-{uuid.uuid4()}@example.com")

    create = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token))
    assert create.status_code == 200
    payload = create.json()
    assert "code" in payload
    assert payload["deep_link"].startswith("https://t.me/mood_tracker_test_bot?start=")

    unauthorized = auth_client.post(
        "/v1/telegram/bot/link",
        json={
            "code": payload["code"],
            "telegram_user_id": 424242,
            "telegram_chat_id": 424242,
            "locale": "ru-RU",
        },
    )
    assert unauthorized.status_code == 401

    linked = auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": payload["code"],
            "telegram_user_id": 424242,
            "telegram_chat_id": 424242,
            "locale": "ru-RU",
        },
    )
    assert linked.status_code == 200
    assert linked.json()["linked"] is True
    assert linked.json()["locale"] == "ru"

    status = auth_client.get("/v1/telegram/link", headers=_auth_headers(token))
    assert status.status_code == 200
    assert status.json()["linked"] is True
    assert status.json()["telegram_user_id"] == 424242

    prefs = auth_client.get("/v1/notification-settings", headers=_auth_headers(token))
    assert prefs.status_code == 200
    assert "telegram" in prefs.json()["channels"]

    reuse = auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": payload["code"],
            "telegram_user_id": 424242,
            "telegram_chat_id": 424242,
        },
    )
    assert reuse.status_code == 400

    me = auth_client.get(
        "/v1/telegram/bot/me",
        headers=_service_headers(),
        params={"telegram_user_id": 424242},
    )
    assert me.status_code == 200
    assert me.json()["linked"] is True
    assert me.json()["onboarding_completed"] is False

    unlinked = auth_client.delete("/v1/telegram/link", headers=_auth_headers(token))
    assert unlinked.status_code == 200
    assert unlinked.json()["linked"] is False


def test_bot_unlink(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-{uuid.uuid4()}@example.com")
    create = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token))
    code = create.json()["code"]
    auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": code,
            "telegram_user_id": 515151,
            "telegram_chat_id": 515151,
        },
    )

    response = auth_client.post(
        "/v1/telegram/bot/unlink",
        headers=_service_headers(),
        json={"telegram_user_id": 515151},
    )
    assert response.status_code == 200
    assert response.json()["linked"] is False

    status = auth_client.get("/v1/telegram/link", headers=_auth_headers(token))
    assert status.json()["linked"] is False


def test_expired_link_code(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-{uuid.uuid4()}@example.com")
    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    user_id = uuid.UUID(me.json()["id"])

    raw = "expired-code-value-xx"
    db.add(
        TelegramLinkCode(
            user_id=user_id,
            code_hash=hash_token(raw),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    db.commit()

    response = auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": raw,
            "telegram_user_id": 999001,
            "telegram_chat_id": 999001,
        },
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]["message"].lower()
    assert response.json()["detail"]["code"] == "telegram_link_code_expired"


def test_cannot_link_same_telegram_to_two_users(
    auth_client: TestClient,
    mailer: FakeEmailService,
    telegram_configured: None,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, f"tg-a-{uuid.uuid4()}@example.com")
    token_b = register_verify_and_login(auth_client, mailer, f"tg-b-{uuid.uuid4()}@example.com")

    code_a = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token_a)).json()[
        "code"
    ]
    auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": code_a,
            "telegram_user_id": 777001,
            "telegram_chat_id": 777001,
        },
    )

    code_b = auth_client.post("/v1/telegram/link-codes", headers=_auth_headers(token_b)).json()[
        "code"
    ]
    conflict = auth_client.post(
        "/v1/telegram/bot/link",
        headers=_service_headers(),
        json={
            "code": code_b,
            "telegram_user_id": 777001,
            "telegram_chat_id": 777001,
        },
    )
    assert conflict.status_code == 409
