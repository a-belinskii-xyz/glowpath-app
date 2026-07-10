import io

from app.models.tag import Tag
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_entry(
    auth_client: TestClient,
    token: str,
    *,
    score: int = 4,
    recorded_at: str = "2026-07-10T12:00:00+03:00",
    note: str | None = None,
    tag_ids: list[str] | None = None,
    headers: dict[str, str] | None = None,
):
    payload: dict = {
        "score": score,
        "recorded_at": recorded_at,
        "tag_ids": tag_ids or [],
    }
    if note is not None:
        payload["note"] = note
    request_headers = _auth_headers(token)
    if headers:
        request_headers.update(headers)
    return auth_client.post("/v1/mood-entries", json=payload, headers=request_headers)


def _user_tag_ids(db: Session, email: str) -> list[str]:
    from app.models.user import User

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    tags = list(db.scalars(select(Tag).where(Tag.user_id == user.id).limit(2)).all())
    assert len(tags) >= 2
    return [str(tag.id) for tag in tags]


def test_create_mood_entry_score_only(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-create@example.com")
    response = _create_entry(auth_client, token)

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 4
    assert body["score_label"] == "good"
    assert body["score_emoji"] == "🙂"
    assert body["note"] is None
    assert body["tags"] == []
    assert body["attachments"] == []
    assert body["recorded_at"].endswith("+00:00") or body["recorded_at"].endswith("Z")


def test_create_with_tags_and_reject_foreign_tag(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "mood-tags-a@example.com")
    register_verify_and_login(auth_client, mailer, "mood-tags-b@example.com")
    tag_ids_a = _user_tag_ids(db, "mood-tags-a@example.com")
    tag_ids_b = _user_tag_ids(db, "mood-tags-b@example.com")

    ok = _create_entry(auth_client, token_a, tag_ids=tag_ids_a)
    assert ok.status_code == 201
    assert {tag["id"] for tag in ok.json()["tags"]} == set(tag_ids_a)

    rejected = _create_entry(auth_client, token_a, tag_ids=[tag_ids_b[0]])
    assert rejected.status_code == 400


def test_patch_partial_and_replace_tags(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-patch@example.com")
    tag_ids = _user_tag_ids(db, "mood-patch@example.com")
    created = _create_entry(auth_client, token, tag_ids=tag_ids)
    entry_id = created.json()["id"]

    patch_response = auth_client.patch(
        f"/v1/mood-entries/{entry_id}",
        json={"note": "updated", "tag_ids": [tag_ids[0]]},
        headers=_auth_headers(token),
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["note"] == "updated"
    assert body["score"] == 4
    assert [tag["id"] for tag in body["tags"]] == [tag_ids[0]]


def test_list_get_delete_and_isolation(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "mood-iso-a@example.com")
    token_b = register_verify_and_login(auth_client, mailer, "mood-iso-b@example.com")

    created = _create_entry(auth_client, token_a)
    entry_id = created.json()["id"]

    list_a = auth_client.get("/v1/mood-entries", headers=_auth_headers(token_a))
    assert list_a.status_code == 200
    assert len(list_a.json()["items"]) == 1

    list_b = auth_client.get("/v1/mood-entries", headers=_auth_headers(token_b))
    assert list_b.status_code == 200
    assert list_b.json()["items"] == []

    foreign_get = auth_client.get(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_b),
    )
    assert foreign_get.status_code == 404

    delete_foreign = auth_client.delete(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_b),
    )
    assert delete_foreign.status_code == 404

    delete_own = auth_client.delete(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_a),
    )
    assert delete_own.status_code == 204

    missing = auth_client.get(
        f"/v1/mood-entries/{entry_id}",
        headers=_auth_headers(token_a),
    )
    assert missing.status_code == 404


def test_attachments_upload_limits_download_delete(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-media@example.com")
    entry_id = _create_entry(auth_client, token).json()["id"]

    photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("shot.jpg", io.BytesIO(b"fake-photo"), "image/jpeg")},
    )
    assert photo.status_code == 201
    photo_body = photo.json()
    assert photo_body["kind"] == "photo"
    assert photo_body["position"] == 1
    assert "storage_key" not in photo_body
    assert len(storage._objects) == 1

    audio = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "audio"},
        files={"file": ("voice.mp3", io.BytesIO(b"fake-audio"), "audio/mpeg")},
    )
    assert audio.status_code == 201
    assert audio.json()["kind"] == "audio"
    assert audio.json()["position"] is None

    second_audio = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "audio"},
        files={"file": ("voice2.mp3", io.BytesIO(b"fake-audio-2"), "audio/mpeg")},
    )
    assert second_audio.status_code == 409

    oversized = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={
            "file": (
                "big.jpg",
                io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)),
                "image/jpeg",
            )
        },
    )
    assert oversized.status_code == 400

    for index in range(4):
        response = auth_client.post(
            f"/v1/mood-entries/{entry_id}/attachments",
            headers=_auth_headers(token),
            data={"kind": "photo"},
            files={"file": (f"p{index}.jpg", io.BytesIO(b"img"), "image/jpeg")},
        )
        assert response.status_code == 201

    sixth_photo = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=_auth_headers(token),
        data={"kind": "photo"},
        files={"file": ("p5.jpg", io.BytesIO(b"img"), "image/jpeg")},
    )
    assert sixth_photo.status_code == 409

    attachment_id = photo_body["id"]
    download = auth_client.get(
        f"/v1/mood-entries/{entry_id}/attachments/{attachment_id}",
        headers=_auth_headers(token),
    )
    assert download.status_code == 200
    assert download.content == b"fake-photo"
    assert download.headers["content-type"].startswith("image/jpeg")

    delete = auth_client.delete(
        f"/v1/mood-entries/{entry_id}/attachments/{attachment_id}",
        headers=_auth_headers(token),
    )
    assert delete.status_code == 204
    assert all(attachment_id not in key for key in storage._objects)


def test_russian_labels_via_accept_language(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "mood-i18n@example.com")
    tag_ids = _user_tag_ids(db, "mood-i18n@example.com")
    response = _create_entry(
        auth_client,
        token,
        score=1,
        tag_ids=[tag_ids[0]],
        headers={"Accept-Language": "ru"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score_label"] == "ужасно"
    assert body["tags"][0]["label"]


def test_tag_groups_list_localized(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tags-list@example.com")

    en = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert en.status_code == 200
    en_items = en.json()["items"]
    assert len(en_items) >= 1
    assert en_items[0]["label"]
    assert len(en_items[0]["tags"]) >= 1

    ru = auth_client.get(
        "/v1/tag-groups",
        headers={**_auth_headers(token), "Accept-Language": "ru"},
    )
    assert ru.status_code == 200
    ru_items = ru.json()["items"]
    assert ru_items[0]["label"] != ""
    assert ru_items[0]["id"] == en_items[0]["id"]


def test_unauthenticated_cannot_create_entry(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/v1/mood-entries",
        json={"score": 3, "recorded_at": "2026-07-10T12:00:00+03:00", "tag_ids": []},
    )
    assert response.status_code == 401
