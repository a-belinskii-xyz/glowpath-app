"""Staff pack editor: per-icon crop, usage hints, order and file replacement."""

from __future__ import annotations

import json
import uuid

import pytest
from app.config import settings
from app.core.marketplace import parse_icon_crop, parse_icon_usage
from app.models.catalog_icon import CatalogIcon
from app.models.user import User
from app.services.marketplace_seed import seed_default_search_tags
from app.services.preset_service import export_preset, import_preset_archive
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

SVG = b"<svg xmlns='http://www.w3.org/2000/svg' width='10' height='20'/>"


@pytest.fixture(autouse=True)
def _enable_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_icon_marketplace", True)
    monkeypatch.setattr(settings, "feature_icon_marketplace_percent", 100)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _staff_token(auth_client: TestClient, mailer: FakeEmailService, db: Session) -> str:
    token = register_verify_and_login(auth_client, mailer, f"pe-{uuid.uuid4()}@example.com")
    me = auth_client.get("/v1/auth/me", headers=_headers(token)).json()
    user = db.get(User, uuid.UUID(me["id"]))
    assert user is not None
    user.is_staff = True
    db.commit()
    return token


def _create_pack(auth_client: TestClient, token: str) -> str:
    response = auth_client.post(
        "/v1/staff/packs",
        json={"labels": {"name": {"en": "Editor", "ru": "Редактор"}}},
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(auth_client: TestClient, token: str, pack_id: str, name: str, **form: str) -> dict:
    response = auth_client.post(
        f"/v1/marketplace/studio/packs/{pack_id}/icons",
        files={"file": (f"{name}.svg", SVG, "image/svg+xml")},
        data={
            "labels": json.dumps({"en": name, "ru": name}),
            "suggested_colors": json.dumps(["#f97316"]),
            **form,
        },
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_parse_icon_crop_and_usage() -> None:
    assert parse_icon_crop({"x": 0.25, "y": 0, "w": 0.5, "h": 1}) == {
        "x": 0.25,
        "y": 0.0,
        "w": 0.5,
        "h": 1.0,
    }
    assert parse_icon_crop({"x": 0.6, "y": 0, "w": 0.5, "h": 1}) is None
    assert parse_icon_crop({"x": 0, "y": 0, "w": 0, "h": 1}) is None
    assert parse_icon_crop({"x": 0, "y": 0, "w": 1}) is None
    assert parse_icon_crop({"x": True, "y": 0, "w": 1, "h": 1}) is None
    assert parse_icon_usage(["goal", "mood", "goal"]) == ["mood", "goal"]
    assert parse_icon_usage(["avatar"]) is None


def test_upload_and_patch_usage_and_crop(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    token = _staff_token(auth_client, mailer, db)
    pack_id = _create_pack(auth_client, token)
    icon = _upload(auth_client, token, pack_id, "fox", suggested_usage=json.dumps(["tag", "mood"]))
    assert icon["suggested_usage"] == ["mood", "tag"]
    assert icon["crop"] is None

    bad_usage = auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={"suggested_usage": ["avatar"]},
        headers=_headers(token),
    )
    assert bad_usage.status_code == 400
    assert bad_usage.json()["detail"]["code"] == "invalid_suggested_usage"

    bad_crop = auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={"crop": {"x": 0.8, "y": 0, "w": 0.5, "h": 0.25}},
        headers=_headers(token),
    )
    assert bad_crop.status_code == 400
    assert bad_crop.json()["detail"]["code"] == "invalid_icon_crop"

    crop = {"x": 0, "y": 0.25, "w": 1, "h": 0.5}
    patched = auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={
            "crop": crop,
            "suggested_usage": ["goal"],
            "suggested_mood_scores": [3],
            "suggested_colors": ["#000000", "#ffffff"],
            "search_tag_slugs": [],
        },
        headers=_headers(token),
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["crop"] == crop
    assert body["suggested_usage"] == ["goal"]
    assert body["suggested_mood_scores"] == [3]

    image = auth_client.get(f"/v1/marketplace/icons/{icon['id']}/image", headers=_headers(token))
    assert image.status_code == 200
    assert image.headers["x-icon-crop"] == "0.0,0.25,1.0,0.5"

    cleared = auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={"clear_crop": True},
        headers=_headers(token),
    )
    assert cleared.json()["crop"] is None
    image = auth_client.get(f"/v1/marketplace/icons/{icon['id']}/image", headers=_headers(token))
    assert "x-icon-crop" not in image.headers


def test_reorder_icons(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = _staff_token(auth_client, mailer, db)
    pack_id = _create_pack(auth_client, token)
    first = _upload(auth_client, token, pack_id, "one")["id"]
    second = _upload(auth_client, token, pack_id, "two")["id"]
    third = _upload(auth_client, token, pack_id, "three")["id"]

    response = auth_client.put(
        f"/v1/marketplace/studio/packs/{pack_id}/icon-order",
        json={"icon_ids": [third, first, second]},
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    assert [icon["id"] for icon in response.json()["icons"]] == [third, first, second]

    partial = auth_client.put(
        f"/v1/marketplace/studio/packs/{pack_id}/icon-order",
        json={"icon_ids": [third, first]},
        headers=_headers(token),
    )
    assert partial.status_code == 400
    assert partial.json()["detail"]["code"] == "icon_order_mismatch"


def test_replace_image_drops_crop_and_old_file(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    token = _staff_token(auth_client, mailer, db)
    pack_id = _create_pack(auth_client, token)
    icon = _upload(auth_client, token, pack_id, "fox")
    auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={"crop": {"x": 0, "y": 0, "w": 1, "h": 0.5}},
        headers=_headers(token),
    )
    old_keys = set(storage._objects)

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    response = auth_client.put(
        f"/v1/marketplace/studio/icons/{icon['id']}/image",
        files={"file": ("fox.png", png, "image/png")},
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == icon["id"]
    assert body["mime_type"] == "image/png"
    assert body["crop"] is None
    assert not old_keys & set(storage._objects)

    image = auth_client.get(f"/v1/marketplace/icons/{icon['id']}/image", headers=_headers(token))
    assert image.content == png


def test_preset_round_trip_keeps_usage_and_crop(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    seed_default_search_tags(db)
    token = _staff_token(auth_client, mailer, db)
    pack_id = _create_pack(auth_client, token)
    icon = _upload(auth_client, token, pack_id, "fox", suggested_usage=json.dumps(["mood"]))
    crop = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.5}
    auth_client.patch(
        f"/v1/marketplace/studio/icons/{icon['id']}",
        json={"crop": crop},
        headers=_headers(token),
    )

    archive, _ = export_preset(
        db, storage=storage, pack_ids=[uuid.UUID(pack_id)], include_achievements=False
    )
    stored = db.get(CatalogIcon, uuid.UUID(icon["id"]))
    assert stored is not None
    stored.crop = None
    stored.suggested_usage = []
    db.commit()

    import_preset_archive(db, storage=storage, data=archive)
    db.commit()
    db.refresh(stored)
    assert stored.crop == crop
    assert stored.suggested_usage == ["mood"]
