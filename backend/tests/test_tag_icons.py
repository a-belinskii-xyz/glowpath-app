import io
import uuid

from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, FakeStorage, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _first_tag(auth_client: TestClient, headers: dict[str, str]) -> tuple[str, dict]:
    listed = auth_client.get("/v1/tag-groups", headers=headers)
    assert listed.status_code == 200
    groups = listed.json()["items"]
    assert groups
    tag = groups[0]["tags"][0]
    return groups[0]["id"], tag


def test_tag_icon_upload_list_select_delete(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tag-icon-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)
    group_id, tag = _first_tag(auth_client, headers)
    tag_id = tag["id"]
    assert tag["icon_type"] == "emoji"
    assert tag["color"]
    assert tag["icon"]

    upload = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}/icons",
        headers=headers,
        files={"file": ("icon.png", io.BytesIO(b"png-bytes"), "image/png")},
    )
    assert upload.status_code == 201
    body = upload.json()
    icon_id = body["id"]
    assert body["tag_id"] == tag_id
    assert body["tag"]["icon_type"] == "upload"
    assert body["tag"]["icon"] == icon_id
    assert len(storage._objects) == 1

    download = auth_client.get(f"/v1/tag-groups/icons/id/{icon_id}", headers=headers)
    assert download.status_code == 200
    assert download.content == b"png-bytes"

    second = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}/icons",
        headers=headers,
        files={"file": ("icon2.png", io.BytesIO(b"new-png"), "image/png")},
    )
    assert second.status_code == 201
    second_id = second.json()["id"]
    assert second_id != icon_id
    assert second.json()["tag"]["icon"] == second_id

    listed = auth_client.get(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}/icons",
        headers=headers,
    )
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["max_per_tag"] == 3
    assert [item["id"] for item in listed_body["items"]] == [icon_id, second_id]

    select_first = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}",
        headers=headers,
        json={"icon_type": "upload", "icon": icon_id},
    )
    assert select_first.status_code == 200
    assert select_first.json()["icon"] == icon_id

    delete = auth_client.delete(f"/v1/tag-groups/icons/id/{icon_id}", headers=headers)
    assert delete.status_code == 204
    assert len(storage._objects) == 1

    groups = auth_client.get("/v1/tag-groups", headers=headers)
    updated = next(
        tag_item
        for group in groups.json()["items"]
        for tag_item in group["tags"]
        if tag_item["id"] == tag_id
    )
    assert updated["icon_type"] == "upload"
    assert updated["icon"] == second_id

    delete_last = auth_client.delete(f"/v1/tag-groups/icons/id/{second_id}", headers=headers)
    assert delete_last.status_code == 204
    assert len(storage._objects) == 0

    groups_after = auth_client.get("/v1/tag-groups", headers=headers)
    after = next(
        tag_item
        for group in groups_after.json()["items"]
        for tag_item in group["tags"]
        if tag_item["id"] == tag_id
    )
    assert after["icon_type"] == "emoji"
    assert after["icon"] == "🏷"


def test_tag_icon_upload_rejects_when_limit_reached(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"tag-icon-limit-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(token)
    group_id, tag = _first_tag(auth_client, headers)
    tag_id = tag["id"]

    for index in range(3):
        response = auth_client.post(
            f"/v1/tag-groups/{group_id}/tags/{tag_id}/icons",
            headers=headers,
            files={"file": (f"icon{index}.png", io.BytesIO(f"png-{index}".encode()), "image/png")},
        )
        assert response.status_code == 201

    fourth = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}/icons",
        headers=headers,
        files={"file": ("extra.png", io.BytesIO(b"extra"), "image/png")},
    )
    assert fourth.status_code == 400
    assert len(storage._objects) == 3


def test_tag_style_patch_and_defaults(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tag-style-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)

    listed = auth_client.get("/v1/tag-groups", headers=headers)
    sunny = next(
        tag for group in listed.json()["items"] for tag in group["tags"] if tag["slug"] == "sunny"
    )
    assert sunny["color"] == "#f59e0b"
    assert sunny["icon_type"] == "emoji"
    assert sunny["icon"] == "☀️"

    group_id = sunny["group_id"]
    patched = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{sunny['id']}",
        headers=headers,
        json={"color": "#34d399", "icon_type": "emoji", "icon": "🌤"},
    )
    assert patched.status_code == 200
    assert patched.json()["color"] == "#34d399"
    assert patched.json()["icon"] == "🌤"

    created = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags",
        headers=headers,
        json={
            "labels": {"en": "Windy"},
            "color": "#60a5fa",
            "icon_type": "emoji",
            "icon": "💨",
        },
    )
    assert created.status_code == 201
    assert created.json()["color"] == "#60a5fa"
    assert created.json()["icon"] == "💨"
