from app.models.tag import Tag
from app.models.user import User
from app.services.tag_service import NEW_TAGS_GROUP_SLUG, tag_label_key
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _headers(token: str, locale: str = "ru") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept-Language": locale}


def _quick(client: TestClient, token: str, label: str):
    return client.post("/v1/tag-groups/quick-tag", json={"label": label}, headers=_headers(token))


def test_label_key_ignores_case_spaces_and_yo() -> None:
    assert tag_label_key("  ДОЖДЬ ") == tag_label_key("дождь")
    assert tag_label_key("Ёлка  у дома") == tag_label_key("елка у дома")
    assert tag_label_key("Дождь") != tag_label_key("Дожди")


def test_quick_tag_created_in_new_tags_group(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token = register_verify_and_login(auth_client, mailer, "quick-new@example.com")
    response = _quick(auth_client, token, "  Град ")
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["tag"]["label"] == "Град"
    assert body["tag"]["icon"] == "🏷"

    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    system = [group for group in groups if group["is_system"]]
    assert len(system) == 1
    assert system[0]["slug"] == NEW_TAGS_GROUP_SLUG
    assert system[0]["label"] == "Новые теги"
    assert system[0]["show_on_entry"] is True
    assert [tag["id"] for tag in system[0]["tags"]] == [body["tag"]["id"]]

    second = _quick(auth_client, token, "Туман")
    assert second.status_code == 201
    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    assert sum(1 for group in groups if group["is_system"]) == 1


def test_quick_tag_reuses_existing_name(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "quick-dup@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    existing = db.scalars(select(Tag).where(Tag.user_id == user.id)).first()
    assert existing is not None
    name = existing.labels.get("ru") or next(iter(existing.labels.values()))

    response = _quick(auth_client, token, f" {name.upper()} ")
    assert response.status_code == 200
    assert response.json()["created"] is False
    assert response.json()["tag"]["id"] == str(existing.id)

    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    assert not any(group["is_system"] for group in groups)


def test_create_and_rename_reject_duplicate_names(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, "quick-rename@example.com")
    rain = _quick(auth_client, token, "Ливень").json()["tag"]
    fog = _quick(auth_client, token, "Туман").json()["tag"]
    group_id = rain["group_id"]

    created = auth_client.post(
        f"/v1/tag-groups/{group_id}/tags",
        json={"labels": {"ru": "ЛИВЕНЬ"}},
        headers=_headers(token),
    )
    assert created.status_code == 409
    assert created.json()["detail"]["code"] == "tag_label_exists"

    renamed = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{fog['id']}",
        json={"labels": {"ru": "ливень"}},
        headers=_headers(token),
    )
    assert renamed.status_code == 409

    same = auth_client.patch(
        f"/v1/tag-groups/{group_id}/tags/{rain['id']}",
        json={"labels": {"ru": "Ливень", "en": "Downpour"}},
        headers=_headers(token),
    )
    assert same.status_code == 200


def test_tag_moves_to_another_group(auth_client: TestClient, mailer: FakeEmailService) -> None:
    token = register_verify_and_login(auth_client, mailer, "quick-move@example.com")
    hail = _quick(auth_client, token, "Град").json()["tag"]
    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    target = next(group for group in groups if not group["is_system"])

    moved = auth_client.patch(
        f"/v1/tag-groups/{hail['group_id']}/tags/{hail['id']}",
        json={"group_id": target["id"]},
        headers=_headers(token),
    )
    assert moved.status_code == 200
    assert moved.json()["group_id"] == target["id"]

    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    target_after = next(group for group in groups if group["id"] == target["id"])
    assert hail["id"] in [tag["id"] for tag in target_after["tags"]]


def test_new_tags_group_does_not_count_toward_visible_limit(
    auth_client: TestClient, mailer: FakeEmailService, monkeypatch
) -> None:
    from app.config import settings

    token = register_verify_and_login(auth_client, mailer, "quick-limit@example.com")
    _quick(auth_client, token, "Град")
    groups = auth_client.get("/v1/tag-groups", headers=_headers(token)).json()["items"]
    visible = sum(1 for g in groups if g["show_on_entry"] and not g["is_system"])
    monkeypatch.setattr(settings, "entry_visible_tag_group_limit", visible + 1)

    created = auth_client.post(
        "/v1/tag-groups",
        json={"labels": {"ru": "Погода дома"}, "show_on_entry": True},
        headers=_headers(token),
    )
    assert created.status_code == 201
