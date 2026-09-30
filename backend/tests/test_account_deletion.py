import io

from app.models.mood_entry import MoodEntry
from app.models.tag import Tag
from app.models.user import User
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_entry_with_photo(auth_client: TestClient, token: str) -> str:
    entry_id = auth_client.post(
        "/v1/mood-entries",
        json={"score": 4, "recorded_at": "2026-07-10T12:00:00+03:00", "note": "hi"},
        headers=_auth_headers(token),
    ).json()["id"]
    photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("shot.jpg", io.BytesIO(b"fake-photo"), "image/jpeg")},
    )
    assert photo.status_code == 201
    return entry_id


def test_delete_requires_confirmation(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "keep-me@example.com")

    response = auth_client.request("DELETE", "/v1/account", headers=_auth_headers(token), json={})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "account_delete_not_confirmed"
    assert db.scalar(select(User).where(User.email == "keep-me@example.com")) is not None


def test_delete_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.request("DELETE", "/v1/account", json={"confirm": True})
    assert response.status_code == 401


def test_delete_removes_user_data_and_files(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "bye@example.com")
    user = db.scalar(select(User).where(User.email == "bye@example.com"))
    assert user is not None
    user_id = user.id
    _create_entry_with_photo(auth_client, token)
    icon = auth_client.post(
        "/v1/mood-preferences/icons/2",
        headers=_auth_headers(token),
        files={"file": ("icon.png", io.BytesIO(b"png-bytes"), "image/png")},
    )
    assert icon.status_code == 201
    assert len(storage._objects) == 2

    response = auth_client.request(
        "DELETE", "/v1/account", headers=_auth_headers(token), json={"confirm": True}
    )
    assert response.status_code == 204

    db.expire_all()
    assert db.get(User, user_id) is None
    assert db.scalar(select(func.count()).where(MoodEntry.user_id == user_id)) == 0
    assert db.scalar(select(func.count()).where(Tag.user_id == user_id)) == 0
    assert storage._objects == {}

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 401

    # The email is free again.
    again = register_verify_and_login(auth_client, mailer, "bye@example.com")
    assert again


def test_delete_leaves_other_users_alone(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
) -> None:
    leaving = register_verify_and_login(auth_client, mailer, "leaving@example.com")
    staying = register_verify_and_login(auth_client, mailer, "staying@example.com")
    _create_entry_with_photo(auth_client, leaving)
    kept_entry = _create_entry_with_photo(auth_client, staying)

    response = auth_client.request(
        "DELETE", "/v1/account", headers=_auth_headers(leaving), json={"confirm": True}
    )
    assert response.status_code == 204

    assert len(storage._objects) == 1
    entry = auth_client.get(f"/v1/mood-entries/{kept_entry}", headers=_auth_headers(staying))
    assert entry.status_code == 200
    assert len(entry.json()["attachments"]) == 1


def test_delete_survives_storage_failure(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
    db: Session,
    monkeypatch,
) -> None:
    from app.core.error_codes import ErrorCode
    from app.services.storage import StorageError

    token = register_verify_and_login(auth_client, mailer, "flaky@example.com")
    _create_entry_with_photo(auth_client, token)

    def broken_delete(*, key: str) -> None:
        raise StorageError("boom", code=ErrorCode.STORAGE_DELETE_FAILED)

    monkeypatch.setattr(storage, "delete_object", broken_delete)
    response = auth_client.request(
        "DELETE", "/v1/account", headers=_auth_headers(token), json={"confirm": True}
    )
    assert response.status_code == 204
    db.expire_all()
    assert db.scalar(select(User).where(User.email == "flaky@example.com")) is None
