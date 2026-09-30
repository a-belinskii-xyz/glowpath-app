import io
from datetime import UTC, datetime
from typing import Any

import pytest
from app.config import settings
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-body"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_entry(auth_client: TestClient, token: str) -> str:
    response = auth_client.post(
        "/v1/mood-entries",
        headers=_auth_headers(token),
        json={"score": 4, "recorded_at": "2026-07-10T12:00:00+03:00", "tag_ids": []},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _send(auth_client: TestClient, token: str, entry_id: str, data: bytes = PNG):
    return auth_client.post(
        f"/v1/mood-entries/{entry_id}/share-image/telegram",
        headers=_auth_headers(token),
        files={"file": ("glowpath.png", io.BytesIO(data), "image/png")},
    )


def _link_telegram(db: Session, email: str, chat_id: int = 555) -> None:
    user = db.scalars(select(User).where(User.email == email)).one()
    user.telegram_user_id = chat_id
    user.telegram_chat_id = chat_id
    user.telegram_linked_at = datetime.now(UTC)
    db.commit()


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_share_image_sends_photo_to_linked_chat(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "share-image@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    entry_id = _create_entry(auth_client, token)
    _link_telegram(db, email)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append({"url": url, **kwargs})
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("app.services.telegram_delivery.httpx.post", fake_post)

    response = _send(auth_client, token, entry_id)

    assert response.status_code == 204
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/bottest-token/sendPhoto")
    assert calls[0]["data"] == {"chat_id": "555"}
    assert calls[0]["files"]["photo"][1] == PNG


def test_share_image_rejects_non_png_and_unlinked(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "share-image-unlinked@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    entry_id = _create_entry(auth_client, token)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")

    def fail_post(url: str, **kwargs: Any) -> _FakeResponse:
        raise AssertionError("Telegram must not be called")

    monkeypatch.setattr("app.services.telegram_delivery.httpx.post", fail_post)

    not_png = _send(auth_client, token, entry_id, data=b"GIF89a")
    assert not_png.status_code == 400
    assert not_png.json()["detail"]["code"] == "share_image_invalid"

    unlinked = _send(auth_client, token, entry_id)
    assert unlinked.status_code == 409
    assert unlinked.json()["detail"]["code"] == "telegram_not_linked"


def test_share_image_other_users_entry_is_not_found(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    owner = register_verify_and_login(auth_client, mailer, "share-owner@example.com")
    entry_id = _create_entry(auth_client, owner)
    stranger = register_verify_and_login(auth_client, mailer, "share-stranger@example.com")
    _link_telegram(db, "share-stranger@example.com", chat_id=777)

    response = _send(auth_client, stranger, entry_id)

    assert response.status_code == 404


def test_share_image_reports_telegram_rejection(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "share-image-blocked@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    entry_id = _create_entry(auth_client, token)
    _link_telegram(db, email, chat_id=888)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    monkeypatch.setattr(
        "app.services.telegram_delivery.httpx.post",
        lambda url, **kwargs: _FakeResponse(
            {"ok": False, "error_code": 403, "description": "bot was blocked by the user"}
        ),
    )

    response = _send(auth_client, token, entry_id)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "telegram_send_rejected"
