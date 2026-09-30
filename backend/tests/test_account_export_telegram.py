import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

import pytest
from app.config import settings
from app.models.user import User
from app.services import account_export_service
from app.services.account_export_service import build_account_export_parts
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _link_telegram(db: Session, email: str, chat_id: int = 777) -> None:
    user = db.scalars(select(User).where(User.email == email)).one()
    user.telegram_user_id = chat_id
    user.telegram_chat_id = chat_id
    user.telegram_linked_at = datetime.now(UTC)
    db.commit()


def _entry_with_photos(auth_client: TestClient, token: str, photos: list[bytes]) -> None:
    entry_id = auth_client.post(
        "/v1/mood-entries",
        json={"score": 4, "recorded_at": "2026-07-10T12:00:00+03:00", "note": "day"},
        headers=_auth_headers(token),
    ).json()["id"]
    for index, data in enumerate(photos):
        response = auth_client.post(
            f"/v1/mood-entries/{entry_id}/attachments",
            headers=_auth_headers(token),
            data={"kind": "photo"},
            files={"file": (f"p{index}.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert response.status_code == 201


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_parts_split_media_and_keep_diary_in_first(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
) -> None:
    email = "parts@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    photos = [bytes([index]) * 40_000 for index in range(3)]
    _entry_with_photos(auth_client, token, photos)
    user = db.scalars(select(User).where(User.email == email)).one()

    archives = build_account_export_parts(
        db, user=user, storage=storage, locale="en", max_part_bytes=120_000
    )

    assert len(archives) >= 2
    zips = [zipfile.ZipFile(io.BytesIO(archive.read())) for archive in archives]
    assert {"diary.json", "entries.csv"} <= set(zips[0].namelist())
    for later in zips[1:]:
        assert "diary.json" not in later.namelist()
    payload = json.loads(zips[0].read("diary.json"))
    attachments = payload["entries"][0]["attachments"]
    assert len(attachments) == 3
    seen = set()
    for attachment in attachments:
        part = zips[attachment["part"] - 1]
        assert attachment["file"] in part.namelist()
        seen.add(part.read(attachment["file"]))
    assert seen == set(photos)


def test_single_part_without_limit(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
) -> None:
    email = "one-part@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    _entry_with_photos(auth_client, token, [b"a" * 40_000, b"b" * 40_000])
    user = db.scalars(select(User).where(User.email == email)).one()

    archives = build_account_export_parts(db, user=user, storage=storage, locale="en")
    assert len(archives) == 1
    payload = json.loads(zipfile.ZipFile(archives[0]).read("diary.json"))
    assert {item["part"] for item in payload["entries"][0]["attachments"]} == {1}


def test_send_export_to_telegram_in_parts(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "tg-export@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    _entry_with_photos(auth_client, token, [b"x" * 40_000, b"y" * 40_000, b"z" * 40_000])
    _link_telegram(db, email)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    monkeypatch.setattr(account_export_service, "TELEGRAM_PART_BYTES", 120_000)
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append({"url": url, **kwargs})
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("app.services.telegram_delivery.httpx.post", fake_post)

    response = auth_client.post(
        "/v1/account/export/telegram",
        headers={**_auth_headers(token), "Accept-Language": "ru"},
    )

    assert response.status_code == 200
    parts = response.json()["parts"]
    assert parts >= 2
    assert len(calls) == parts
    assert all(call["url"].endswith("/bottest-token/sendDocument") for call in calls)
    assert calls[0]["data"]["chat_id"] == "777"
    assert calls[0]["data"]["caption"] == f"GlowPath: ваш дневник, часть 1 из {parts}"
    filename, data, content_type = calls[0]["files"]["document"]
    assert filename.endswith(f"-part1of{parts}.zip")
    assert content_type == "application/zip"
    assert "diary.json" in zipfile.ZipFile(io.BytesIO(data)).namelist()


def test_send_export_single_file_caption(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "tg-small@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    _link_telegram(db, email, chat_id=778)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append({"url": url, **kwargs})
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("app.services.telegram_delivery.httpx.post", fake_post)

    response = auth_client.post("/v1/account/export/telegram", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json() == {"parts": 1}
    assert calls[0]["data"]["caption"] == "GlowPath: your diary"
    assert not calls[0]["files"]["document"][0].count("part")


def test_send_export_requires_linked_telegram(
    auth_client: TestClient,
    mailer: FakeEmailService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tg-none@example.com")
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")

    response = auth_client.post("/v1/account/export/telegram", headers=_auth_headers(token))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "telegram_not_linked"


def test_send_export_reports_blocked_bot(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "tg-blocked@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    _link_telegram(db, email, chat_id=779)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    monkeypatch.setattr(
        "app.services.telegram_delivery.httpx.post",
        lambda url, **kwargs: _FakeResponse({"ok": False, "error_code": 403}),
    )

    response = auth_client.post("/v1/account/export/telegram", headers=_auth_headers(token))

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "telegram_send_rejected"
