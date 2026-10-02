from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest
from app.config import settings
from app.models.telegram_login_request import TelegramLoginRequest
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

START_URL = "/v1/auth/telegram/bot-login"
POLL_URL = "/v1/auth/telegram/bot-login/poll"
CONFIRM_URL = "/v1/telegram/bot/login-confirm"
SERVICE_HEADERS = {"X-Telegram-Bot-Service-Token": "test-service-token"}


@pytest.fixture(autouse=True)
def _bot_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "telegram_bot_username", "glowpath_test_bot")
    monkeypatch.setattr(settings, "telegram_bot_service_token", "test-service-token")
    monkeypatch.setattr(settings, "telegram_link_code_expire_minutes", 10)


def _start(client: TestClient) -> tuple[str, str]:
    response = client.post(START_URL, json={"timezone": "Europe/Moscow"})
    assert response.status_code == 200
    body = response.json()
    link = urlparse(body["deep_link"])
    assert link.netloc == "t.me" and link.path == "/glowpath_test_bot"
    start = link.query.removeprefix("start=")
    assert start.startswith("login_")
    assert len(start) <= 64
    return body["poll_token"], start.removeprefix("login_")


def _confirm(client: TestClient, code: str, telegram_user_id: int = 7001) -> int:
    response = client.post(
        CONFIRM_URL,
        headers=SERVICE_HEADERS,
        json={"code": code, "telegram_user_id": telegram_user_id, "locale": "ru"},
    )
    return response.status_code


def test_bot_login_creates_account_after_confirmation(
    auth_client: TestClient,
    db: Session,
) -> None:
    poll_token, code = _start(auth_client)

    assert auth_client.post(POLL_URL, json={"poll_token": poll_token}).json() == {
        "status": "pending",
        "access_token": None,
        "refresh_token": None,
        "user_created": None,
    }

    assert _confirm(auth_client, code) == 204
    confirmed = auth_client.post(POLL_URL, json={"poll_token": poll_token}).json()

    assert confirmed["status"] == "confirmed"
    assert confirmed["access_token"] and confirmed["refresh_token"]
    assert confirmed["user_created"] is True
    user = db.scalar(select(User).where(User.telegram_user_id == 7001))
    assert user is not None
    assert user.timezone == "Europe/Moscow"
    assert user.telegram_locale == "ru"

    me = auth_client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {confirmed['access_token']}"}
    )
    assert me.status_code == 200

    # Tokens are handed out once.
    again = auth_client.post(POLL_URL, json={"poll_token": poll_token}).json()
    assert again["status"] == "expired"


def test_bot_login_signs_in_existing_telegram_user(
    auth_client: TestClient,
    db: Session,
) -> None:
    first_poll, first_code = _start(auth_client)
    _confirm(auth_client, first_code, telegram_user_id=7002)
    auth_client.post(POLL_URL, json={"poll_token": first_poll})

    poll_token, code = _start(auth_client)
    _confirm(auth_client, code, telegram_user_id=7002)
    body = auth_client.post(POLL_URL, json={"poll_token": poll_token}).json()

    assert body["status"] == "confirmed"
    assert body["user_created"] is None
    users = db.scalars(select(User).where(User.telegram_user_id == 7002)).all()
    assert len(users) == 1


def test_code_cannot_be_confirmed_twice(auth_client: TestClient) -> None:
    _, code = _start(auth_client)
    assert _confirm(auth_client, code) == 204
    assert _confirm(auth_client, code, telegram_user_id=9999) == 400


def test_unknown_code_is_rejected(auth_client: TestClient) -> None:
    assert _confirm(auth_client, "not-a-real-code") == 400


def test_expired_request_cannot_be_confirmed_or_polled(
    auth_client: TestClient,
    db: Session,
) -> None:
    poll_token, code = _start(auth_client)
    row = db.scalars(select(TelegramLoginRequest)).all()[-1]
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    assert _confirm(auth_client, code) == 400
    assert auth_client.post(POLL_URL, json={"poll_token": poll_token}).json()["status"] == (
        "expired"
    )


def test_confirm_requires_bot_service_token(auth_client: TestClient) -> None:
    _, code = _start(auth_client)
    response = auth_client.post(
        CONFIRM_URL, json={"code": code, "telegram_user_id": 7003, "locale": None}
    )
    assert response.status_code in {401, 403}


def test_start_needs_configured_bot(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_username", "")
    response = auth_client.post(START_URL, json={"timezone": "UTC"})
    assert response.status_code == 503


def test_bot_login_keeps_signup_source_from_site(auth_client: TestClient, db: Session) -> None:
    response = auth_client.post(START_URL, json={"timezone": "Europe/Minsk", "signup_source": "vk"})
    assert response.status_code == 200
    body = response.json()
    code = urlparse(body["deep_link"]).query.removeprefix("start=login_")

    assert _confirm(auth_client, code, telegram_user_id=7055) == 204
    assert auth_client.post(POLL_URL, json={"poll_token": body["poll_token"]}).json()["status"] == (
        "confirmed"
    )
    user = db.scalar(select(User).where(User.telegram_user_id == 7055))
    assert user is not None
    assert user.signup_source == "vk"
