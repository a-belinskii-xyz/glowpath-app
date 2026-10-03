"""Staff achievement editor: criteria specs, create/edit/archive, image icons, presets."""

from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from app.config import settings
from app.core.achievement_criteria import (
    CRITERIA_SPECS,
    InvalidCriteriaError,
    normalize_criteria,
)
from app.core.achievements import CRITERIA_TYPES
from app.models.achievement import Achievement
from app.models.icon_pack import IconPack
from app.models.user import User
from app.services.preset_service import export_preset, import_preset_archive
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture(autouse=True)
def _enable_achievements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_achievements", True)
    monkeypatch.setattr(settings, "feature_achievements_percent", 100)
    monkeypatch.setattr(settings, "feature_achievements_emails", "")
    monkeypatch.setattr(settings, "feature_achievements_user_ids", "")
    monkeypatch.setattr(settings, "feature_icon_marketplace", True)
    monkeypatch.setattr(settings, "feature_icon_marketplace_percent", 100)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    prefix: str,
    *,
    staff: bool = False,
) -> tuple[str, User]:
    token = register_verify_and_login(auth_client, mailer, f"{prefix}-{uuid.uuid4()}@example.com")
    me = auth_client.get("/v1/auth/me", headers=_headers(token))
    user = db.get(User, uuid.UUID(me.json()["id"]))
    assert user is not None
    if staff:
        user.is_staff = True
        db.commit()
    return token, user


def _create_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "labels": {"en": "Ten happy days", "ru": "Десять хороших дней"},
        "descriptions": {"en": "Log a 5 ten times.", "ru": "Поставь 5 десять раз."},
        "category": "collection",
        "visibility": "visible",
        "criteria": {"type": "score_count", "score": 5, "count": 10},
        "rewards": [{"kind": "tokens", "amount": 20}],
        "emoji": "🌞",
    }
    body.update(overrides)
    return body


def test_every_criteria_type_has_a_spec() -> None:
    assert set(CRITERIA_SPECS) == CRITERIA_TYPES


def test_normalize_criteria_validates_params() -> None:
    assert normalize_criteria({"type": "entry_count", "count": "7", "junk": 1}) == {
        "type": "entry_count",
        "count": 7,
    }
    assert normalize_criteria({"type": "attachment_count", "count": 2}) == {
        "type": "attachment_count",
        "count": 2,
    }
    assert normalize_criteria({"type": "calendar_match", "weekday": "4", "day": 13}) == {
        "type": "calendar_match",
        "weekday": 4,
        "day": 13,
    }
    bad = [
        {"type": "nope"},
        {"type": "entry_count"},
        {"type": "entry_count", "count": 0},
        {"type": "entry_count", "count": 1.5},
        {"type": "score_count", "score": 6, "count": 1},
        {"type": "attachment_count", "kind": "video", "count": 1},
        {"type": "calendar_match"},
        {"type": "local_hour_range", "hour_from": 5, "hour_to": 5, "count": 1},
    ]
    for raw in bad:
        with pytest.raises(InvalidCriteriaError):
            normalize_criteria(raw)


def test_non_staff_cannot_use_editor(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    token, _ = _login(auth_client, mailer, db, "ach-user")
    for method, path in (
        ("get", "/v1/staff/achievements"),
        ("get", "/v1/staff/achievements/criteria-types"),
        ("post", "/v1/staff/achievements"),
    ):
        response = getattr(auth_client, method)(path, headers=_headers(token))
        assert response.status_code in {403, 422}


def test_create_edit_publish_and_unlock(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    staff_token, _ = _login(auth_client, mailer, db, "ach-staff", staff=True)
    specs = auth_client.get("/v1/staff/achievements/criteria-types", headers=_headers(staff_token))
    assert specs.status_code == 200
    assert {item["type"] for item in specs.json()["items"]} == CRITERIA_TYPES

    created = auth_client.post(
        "/v1/staff/achievements",
        headers=_headers(staff_token),
        json=_create_body(criteria={"type": "entry_count", "count": 1}),
    )
    assert created.status_code == 201, created.text
    achievement = created.json()
    assert achievement["status"] == "draft"
    assert achievement["slug"] == "ten_happy_days"
    assert achievement["icon"] == "🌞"
    assert achievement["rewards"] == [
        {
            "kind": "tokens",
            "amount": 20,
            "pack_id": None,
            "catalog_icon_id": None,
            "icon_pack_id": None,
            "label": None,
        }
    ]

    # Same name again gets a fresh slug.
    again = auth_client.post(
        "/v1/staff/achievements", headers=_headers(staff_token), json=_create_body()
    )
    assert again.status_code == 201
    assert again.json()["slug"] == "ten_happy_days_2"

    invalid = auth_client.patch(
        f"/v1/staff/achievements/{achievement['id']}",
        headers=_headers(staff_token),
        json={"criteria": {"type": "score_count", "score": 9, "count": 1}},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_achievement_criteria"

    user_token, user = _login(auth_client, mailer, db, "ach-player")
    entry = auth_client.post(
        "/v1/mood-entries",
        headers=_headers(user_token),
        json={"score": 4, "recorded_at": "2026-01-15T12:00:00+00:00"},
    )
    assert entry.status_code == 201
    # Draft achievements are invisible to users.
    listed = auth_client.get("/v1/achievements", headers=_headers(user_token)).json()["items"]
    assert achievement["id"] not in {item["id"] for item in listed}

    published = auth_client.patch(
        f"/v1/staff/achievements/{achievement['id']}",
        headers=_headers(staff_token),
        json={"status": "published", "labels": {"en": "First light"}},
    )
    assert published.status_code == 200
    assert published.json()["labels"] == {"en": "First light", "ru": "First light"}

    listed = auth_client.get("/v1/achievements", headers=_headers(user_token)).json()["items"]
    mine = next(item for item in listed if item["id"] == achievement["id"])
    assert mine["unlocked"] is True
    assert mine["name"] == "First light"

    staff_list = auth_client.get("/v1/staff/achievements", headers=_headers(staff_token))
    row = next(item for item in staff_list.json()["items"] if item["id"] == achievement["id"])
    assert row["unlocked_count"] == 1

    archived = auth_client.patch(
        f"/v1/staff/achievements/{achievement['id']}",
        headers=_headers(staff_token),
        json={"status": "archived"},
    )
    assert archived.json()["status"] == "archived"
    listed = auth_client.get("/v1/achievements", headers=_headers(user_token)).json()["items"]
    assert achievement["id"] not in {item["id"] for item in listed}
    assert user.id is not None


def test_reward_must_point_at_existing_pack(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    staff_token, _ = _login(auth_client, mailer, db, "ach-reward", staff=True)
    response = auth_client.post(
        "/v1/staff/achievements",
        headers=_headers(staff_token),
        json=_create_body(rewards=[{"kind": "icon_pack", "pack_id": str(uuid.uuid4())}]),
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_achievement_reward"


def test_image_icon_upload_access_and_preset_roundtrip(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    staff_token, _ = _login(auth_client, mailer, db, "ach-image", staff=True)
    slug = f"secret_image_{uuid.uuid4().hex[:8]}"
    created = auth_client.post(
        "/v1/staff/achievements",
        headers=_headers(staff_token),
        json=_create_body(slug=slug, visibility="secret"),
    ).json()

    rejected = auth_client.put(
        f"/v1/staff/achievements/{created['id']}/icon",
        headers=_headers(staff_token),
        files={"file": ("icon.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 400

    uploaded = auth_client.put(
        f"/v1/staff/achievements/{created['id']}/icon",
        headers=_headers(staff_token),
        files={"file": ("icon.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["icon_type"] == "image"

    staff_icon = auth_client.get(
        f"/v1/achievements/{created['id']}/icon", headers=_headers(staff_token)
    )
    assert staff_icon.status_code == 200
    assert staff_icon.content == PNG
    assert staff_icon.headers["content-type"] == "image/png"

    auth_client.patch(
        f"/v1/staff/achievements/{created['id']}",
        headers=_headers(staff_token),
        json={"status": "published"},
    )
    user_token, _ = _login(auth_client, mailer, db, "ach-image-user")
    # A locked secret achievement doesn't reveal its icon.
    hidden = auth_client.get(f"/v1/achievements/{created['id']}/icon", headers=_headers(user_token))
    assert hidden.status_code == 404

    data, _manifest = export_preset(db, storage=storage, pack_ids=[], include_achievements=True)
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.read(f"achievements/icons/{slug}.png") == PNG

    db.execute(delete(Achievement).where(Achievement.slug == slug))
    db.commit()
    report = import_preset_archive(db, storage=storage, data=data)
    db.commit()
    assert slug in report.achievements
    restored = db.scalar(select(Achievement).where(Achievement.slug == slug))
    assert restored is not None
    assert restored.icon_type == "image"
    assert restored.icon_storage_key is not None
    assert storage.get_object(key=restored.icon_storage_key) == PNG

    # Picking an emoji switches back from the image.
    switched = auth_client.patch(
        f"/v1/staff/achievements/{restored.id}",
        headers=_headers(staff_token),
        json={"emoji": "🦊"},
    )
    assert switched.json()["icon_type"] == "emoji"
    assert switched.json()["icon"] == "🦊"


def test_starter_content_adds_only_missing_achievements(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    user_token, _ = _login(auth_client, mailer, db, "starter-user")
    forbidden = auth_client.post("/v1/staff/presets/starter", headers=_headers(user_token))
    assert forbidden.status_code == 403

    slugs = ["first_entry", "consecutive_days_7", "email_arrival"]
    db.execute(delete(Achievement).where(Achievement.slug.in_(slugs)))
    db.commit()

    staff_token, _ = _login(auth_client, mailer, db, "starter-staff", staff=True)
    first = auth_client.post("/v1/staff/presets/starter", headers=_headers(staff_token))
    assert first.status_code == 200, first.text
    report = first.json()
    assert report["packs"] == ["essentials"]
    assert report["icons"] > 0
    assert {"first_entry", "consecutive_days_7"} <= set(report["achievements"])
    # Archived catalog entries are not created.
    assert "email_arrival" not in report["achievements"]

    week = db.scalar(select(Achievement).where(Achievement.slug == "consecutive_days_7"))
    assert week is not None
    kinds = {reward.kind for reward in week.rewards}
    has_stub_pack = db.scalar(select(IconPack.id).where(IconPack.slug == "random-pics"))
    assert kinds == ({"tokens", "icon_pack"} if has_stub_pack else {"tokens"})

    entry = db.scalar(select(Achievement).where(Achievement.slug == "first_entry"))
    assert entry is not None
    edited = auth_client.patch(
        f"/v1/staff/achievements/{entry.id}",
        headers=_headers(staff_token),
        json={"labels": {"en": "Edited by staff"}},
    )
    assert edited.status_code == 200

    again = auth_client.post("/v1/staff/presets/starter", headers=_headers(staff_token))
    assert again.status_code == 200
    assert again.json()["achievements"] == []
    db.expire_all()
    entry = db.scalar(select(Achievement).where(Achievement.slug == "first_entry"))
    assert entry is not None
    assert entry.labels["en"] == "Edited by staff"


def test_startup_seed_adds_missing_builtin_achievements(db: Session) -> None:
    from app.jobs.seed_builtin import seed_builtin_content

    db.execute(delete(Achievement).where(Achievement.slug.in_(["first_entry", "streak_3"])))
    existing = db.scalar(select(Achievement).where(Achievement.slug == "first_note"))
    if existing is not None:
        existing.labels = {"en": "Kept", "ru": "Оставлено"}
    db.flush()

    added = {achievement.slug for achievement in seed_builtin_content(db)}
    assert {"first_entry", "streak_3"} <= added
    assert "email_arrival" not in added
    if existing is not None:
        assert "first_note" not in added
        assert existing.labels["en"] == "Kept"
    assert seed_builtin_content(db) == []
