from app.models.tag import Tag
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tag_group_crud(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-crud@example.com")
    headers = _auth_headers(token)

    created = auth_client.post(
        "/v1/tag-groups",
        json={"labels": {"en": "Custom"}},
        headers=headers,
    )
    assert created.status_code == 201
    group = created.json()
    assert group["slug"] == "custom"
    assert group["label"] == "Custom"
    assert group["tags"] == []
    group_id = group["id"]

    patched = auth_client.patch(
        f"/v1/tag-groups/{group_id}",
        json={"labels": {"en": "Customized"}},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["label"] == "Customized"

    deleted = auth_client.delete(f"/v1/tag-groups/{group_id}", headers=headers)
    assert deleted.status_code == 204

    missing = auth_client.get("/v1/tag-groups", headers=headers)
    assert missing.status_code == 200
    assert all(item["id"] != group_id for item in missing.json()["items"])


def test_tag_crud_auto_slug_and_sort_order(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-item-crud@example.com")
    headers = _auth_headers(token)

    groups = auth_client.get("/v1/tag-groups", headers=headers)
    assert groups.status_code == 200
    group = groups.json()["items"][0]
    group_id = group["id"]
    max_sort = max((tag["sort_order"] for tag in group["tags"]), default=-1)

    created = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags",
        json={"labels": {"en": "My tag"}},
        headers=headers,
    )
    assert created.status_code == 201
    tag = created.json()
    assert tag["slug"] == "my_tag"
    assert tag["label"] == "My tag"
    assert tag["group_id"] == group_id
    assert tag["sort_order"] == max_sort + 1
    tag_id = tag["id"]

    duplicate = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags",
        json={"slug": "my_tag", "labels": {"en": "Again"}},
        headers=headers,
    )
    assert duplicate.status_code == 409

    patched = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}",
        json={"labels": {"en": "Updated tag"}},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["label"] == "Updated tag"

    deleted = auth_client.delete(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}",
        headers=headers,
    )
    assert deleted.status_code == 204


def test_reorder_tags(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-reorder@example.com")
    headers = _auth_headers(token)

    groups = auth_client.get("/v1/tag-groups", headers=headers).json()["items"]
    group = next(item for item in groups if len(item["tags"]) >= 2)
    original_ids = [tag["id"] for tag in group["tags"]]
    reordered_ids = list(reversed(original_ids))

    response = auth_client.put(
        f"/v1/tag-groups/{group['id']}/tags/reorder",
        json={"ordered_ids": reordered_ids},
        headers=headers,
    )
    assert response.status_code == 200
    assert [tag["id"] for tag in response.json()["tags"]] == reordered_ids


def test_cannot_delete_tag_in_use(
    auth_client: TestClient,
    mailer,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-in-use@example.com")
    headers = _auth_headers(token)

    user = db.scalar(select(User).where(User.email == "tag-in-use@example.com"))
    assert user is not None
    tag = db.scalar(select(Tag).where(Tag.user_id == user.id).limit(1))
    assert tag is not None

    entry = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 3,
            "recorded_at": "2026-07-10T12:00:00+03:00",
            "tag_ids": [str(tag.id)],
        },
        headers=headers,
    )
    assert entry.status_code == 201

    blocked_tag = auth_client.delete(
        f"/v1/tag-groups/{tag.group_id}/tags/{tag.id}",
        headers=headers,
    )
    assert blocked_tag.status_code == 409

    blocked_group = auth_client.delete(
        f"/v1/tag-groups/{tag.group_id}",
        headers=headers,
    )
    assert blocked_group.status_code == 409


def test_tag_isolation_between_users(
    auth_client: TestClient,
    mailer,
) -> None:
    token_a = register_verify_and_login(auth_client, mailer, "tag-iso-a@example.com")
    token_b = register_verify_and_login(auth_client, mailer, "tag-iso-b@example.com")

    groups_a = auth_client.get("/v1/tag-groups", headers=_auth_headers(token_a))
    group_id = groups_a.json()["items"][0]["id"]
    tag_id = groups_a.json()["items"][0]["tags"][0]["id"]

    foreign_patch = auth_client.patch(
        f"/v1/tag-groups/{group_id}",
        json={"labels": {"en": "Hacked"}},
        headers=_auth_headers(token_b),
    )
    assert foreign_patch.status_code == 404

    foreign_tag = auth_client.delete(
        f"/v1/tag-groups/{group_id}/tags/{tag_id}",
        headers=_auth_headers(token_b),
    )
    assert foreign_tag.status_code == 404


def test_invalid_slug_rejected(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-slug@example.com")
    response = auth_client.post(
        "/v1/tag-groups",
        json={"slug": "Bad Slug!", "labels": {"en": "Nope"}},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422


def test_default_groups_show_on_entry(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "tag-visible-default@example.com")
    response = auth_client.get("/v1/tag-groups", headers=_auth_headers(token))
    assert response.status_code == 200
    payload = response.json()
    limit = payload["entry_visible_tag_group_limit"]
    assert limit >= 1
    visible = [item for item in payload["items"] if item["show_on_entry"]]
    hidden = [item for item in payload["items"] if not item["show_on_entry"]]
    assert len(visible) == min(limit, len(payload["items"]))
    assert len(visible) + len(hidden) == len(payload["items"])


def test_show_on_entry_toggle_and_limit(
    auth_client: TestClient,
    mailer,
    monkeypatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "entry_visible_tag_group_limit", 2)

    token = register_verify_and_login(auth_client, mailer, "tag-visible-limit@example.com")
    headers = _auth_headers(token)

    listed = auth_client.get("/v1/tag-groups", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["entry_visible_tag_group_limit"] == 2
    groups = listed.json()["items"]
    assert len(groups) >= 3
    visible = [group for group in groups if group["show_on_entry"]]
    hidden = [group for group in groups if not group["show_on_entry"]]
    assert len(visible) == 2
    assert len(hidden) >= 1

    # Creating a custom group defaults to hidden.
    created = auth_client.post(
        "/v1/tag-groups",
        json={"labels": {"en": "Custom hidden"}},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["show_on_entry"] is False
    custom_id = created.json()["id"]

    # Cannot enable another visible group when already at the limit.
    blocked = auth_client.patch(
        f"/v1/tag-groups/{custom_id}",
        json={"show_on_entry": True},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert "at most 2" in blocked.json()["detail"]

    # Free a slot, then enable the custom group.
    freed = auth_client.patch(
        f"/v1/tag-groups/{visible[0]['id']}",
        json={"show_on_entry": False},
        headers=headers,
    )
    assert freed.status_code == 200

    enabled = auth_client.patch(
        f"/v1/tag-groups/{custom_id}",
        json={"show_on_entry": True},
        headers=headers,
    )
    assert enabled.status_code == 200
    assert enabled.json()["show_on_entry"] is True
