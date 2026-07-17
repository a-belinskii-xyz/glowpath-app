import io
import uuid

from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, FakeStorage, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_mood_icon_upload_list_select_delete(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"mood-icon-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)

    upload = auth_client.post(
        "/v1/mood-preferences/icons/2",
        headers=headers,
        files={"file": ("icon.png", io.BytesIO(b"png-bytes"), "image/png")},
    )
    assert upload.status_code == 201
    body = upload.json()
    icon_id = body["id"]
    assert body["score"] == 2
    assert body["preferences"]["scores"]["2"]["icon_type"] == "upload"
    assert body["preferences"]["scores"]["2"]["icon"] == icon_id
    assert len(storage._objects) == 1

    download = auth_client.get(
        f"/v1/mood-preferences/icons/id/{icon_id}",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content == b"png-bytes"

    second = auth_client.post(
        "/v1/mood-preferences/icons/2",
        headers=headers,
        files={"file": ("icon2.png", io.BytesIO(b"new-png"), "image/png")},
    )
    assert second.status_code == 201
    second_id = second.json()["id"]
    assert second_id != icon_id
    assert len(storage._objects) == 2
    assert second.json()["preferences"]["scores"]["2"]["icon"] == second_id

    listed = auth_client.get("/v1/mood-preferences/icons?score=2", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["max_per_score"] == 3
    assert [item["id"] for item in listed_body["items"]] == [icon_id, second_id]

    select_first = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"2": {"icon_type": "upload", "icon": icon_id}}},
    )
    assert select_first.status_code == 200
    assert select_first.json()["scores"]["2"]["icon"] == icon_id

    delete = auth_client.delete(f"/v1/mood-preferences/icons/id/{icon_id}", headers=headers)
    assert delete.status_code == 204
    assert len(storage._objects) == 1

    prefs = auth_client.get("/v1/mood-preferences", headers=headers)
    assert prefs.json()["scores"]["2"]["icon_type"] == "upload"
    assert prefs.json()["scores"]["2"]["icon"] == second_id

    delete_last = auth_client.delete(
        f"/v1/mood-preferences/icons/id/{second_id}",
        headers=headers,
    )
    assert delete_last.status_code == 204
    assert len(storage._objects) == 0

    prefs_after = auth_client.get("/v1/mood-preferences", headers=headers)
    assert prefs_after.json()["scores"]["2"]["icon_type"] == "emoji"
    assert prefs_after.json()["scores"]["2"]["icon"] == "😞"


def test_mood_icon_upload_rejects_when_limit_reached(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"mood-icon-limit-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(token)

    for index in range(3):
        response = auth_client.post(
            "/v1/mood-preferences/icons/4",
            headers=headers,
            files={"file": (f"icon{index}.png", io.BytesIO(f"png-{index}".encode()), "image/png")},
        )
        assert response.status_code == 201

    fourth = auth_client.post(
        "/v1/mood-preferences/icons/4",
        headers=headers,
        files={"file": ("extra.png", io.BytesIO(b"extra"), "image/png")},
    )
    assert fourth.status_code == 400
    assert len(storage._objects) == 3


def test_mood_icon_upload_rejects_oversized_file(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"mood-icon-big-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(token)

    response = auth_client.post(
        "/v1/mood-preferences/icons/1",
        headers=headers,
        files={
            "file": (
                "big.png",
                io.BytesIO(b"x" * (512 * 1024 + 1)),
                "image/png",
            )
        },
    )
    assert response.status_code == 400
    assert len(storage._objects) == 0


def test_mood_icon_upload_rejects_invalid_mime(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client,
        mailer,
        f"mood-icon-mime-{uuid.uuid4()}@example.com",
    )
    headers = _auth_headers(token)

    response = auth_client.post(
        "/v1/mood-preferences/icons/3",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    assert len(storage._objects) == 0


def test_mood_icon_download_requires_owner(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token_a = register_verify_and_login(
        auth_client, mailer, f"mood-icon-a-{uuid.uuid4()}@example.com"
    )
    token_b = register_verify_and_login(
        auth_client, mailer, f"mood-icon-b-{uuid.uuid4()}@example.com"
    )

    upload = auth_client.post(
        "/v1/mood-preferences/icons/5",
        headers=_auth_headers(token_a),
        files={"file": ("star.png", io.BytesIO(b"star"), "image/png")},
    )
    icon_id = upload.json()["id"]

    forbidden = auth_client.get(
        f"/v1/mood-preferences/icons/id/{icon_id}",
        headers=_auth_headers(token_b),
    )
    assert forbidden.status_code == 404
