"""Staff console: user lookup, official packs, and catalog presets."""

from __future__ import annotations

import io
import json
import uuid
import zipfile

import pytest
from app.config import settings
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.icon_pack import IconPack
from app.models.icon_search_tag import IconSearchTag
from app.models.user import User
from app.services.preset_service import export_preset, import_preset_archive
from app.services.storage import FakeStorage
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

SVG = b"<svg xmlns='http://www.w3.org/2000/svg'/>"


@pytest.fixture(autouse=True)
def _enable_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _create_official_pack_with_icons(
    auth_client: TestClient, token: str, *, slug: str
) -> dict[str, object]:
    created = auth_client.post(
        "/v1/staff/packs",
        headers=_headers(token),
        json={
            "labels": {"name": {"en": "Weather", "ru": "Погода"}},
            "slug": slug,
            "price_tokens": 40,
            "sort_order": 30,
        },
    )
    assert created.status_code == 201, created.text
    pack = created.json()
    assert pack["is_official"] is True
    assert pack["status"] == "draft"
    for name, label in (("sun", "Sun"), ("rain", "Rain")):
        upload = auth_client.post(
            f"/v1/marketplace/studio/packs/{pack['id']}/icons",
            headers=_headers(token),
            files={"file": (f"{name}.svg", SVG, "image/svg+xml")},
            data={
                "labels": json.dumps({"en": label, "ru": label}),
                "suggested_colors": json.dumps(["#f59e0b"]),
                "suggested_mood_scores": json.dumps([4]),
                "search_tag_slugs": json.dumps([]),
                "slug": name,
            },
        )
        assert upload.status_code == 201, upload.text
    return pack


def test_me_exposes_staff_flag_and_staff_routes_are_guarded(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    user_token, _user = _login(auth_client, mailer, db, "staff-guard-user")
    staff_token, _staff = _login(auth_client, mailer, db, "staff-guard-staff", staff=True)

    assert auth_client.get("/v1/auth/me", headers=_headers(user_token)).json()["is_staff"] is False
    assert auth_client.get("/v1/auth/me", headers=_headers(staff_token)).json()["is_staff"] is True

    for method, path in (
        ("get", "/v1/staff/users"),
        ("post", "/v1/staff/packs"),
        ("get", "/v1/staff/presets/export"),
    ):
        response = getattr(auth_client, method)(path, headers=_headers(user_token))
        assert response.status_code in {403, 422}
        if response.status_code == 403:
            assert response.json()["detail"]["code"] == "staff_required"


def test_staff_finds_user_and_grants_tokens(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    staff_token, _staff = _login(auth_client, mailer, db, "staff-grant-staff", staff=True)
    _user_token, user = _login(auth_client, mailer, db, "staff-grant-target")
    assert user.email is not None

    found = auth_client.get(
        "/v1/staff/users", params={"q": user.email}, headers=_headers(staff_token)
    )
    assert found.status_code == 200
    items = found.json()["items"]
    assert [item["id"] for item in items] == [str(user.id)]
    assert items[0]["balance"] == 0

    grant = auth_client.post(
        "/v1/wallet/staff/grants",
        headers=_headers(staff_token),
        json={"user_id": str(user.id), "amount": 75, "note": "contest"},
    )
    assert grant.status_code == 200
    assert grant.json()["balance"] == 75

    by_id = auth_client.get(
        "/v1/staff/users", params={"q": str(user.id)}, headers=_headers(staff_token)
    )
    assert by_id.json()["items"][0]["balance"] == 75

    ledger = auth_client.get(f"/v1/staff/users/{user.id}/ledger", headers=_headers(staff_token))
    assert ledger.status_code == 200
    assert ledger.json()["items"][0]["note"] == "contest"


def test_staff_official_pack_lifecycle(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    staff_token, _staff = _login(auth_client, mailer, db, "staff-pack", staff=True)
    slug = f"weather-{uuid.uuid4().hex[:6]}"
    pack = _create_official_pack_with_icons(auth_client, staff_token, slug=slug)

    published = auth_client.post(
        f"/v1/marketplace/staff/packs/{pack['id']}/publish", headers=_headers(staff_token)
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["icon_count"] == 2

    # Official packs stay editable after publishing (staff can keep adding icons).
    extra = auth_client.post(
        f"/v1/marketplace/studio/packs/{pack['id']}/icons",
        headers=_headers(staff_token),
        files={"file": ("snow.svg", SVG, "image/svg+xml")},
        data={"labels": json.dumps({"en": "Snow"}), "suggested_colors": json.dumps(["#60a5fa"])},
    )
    assert extra.status_code == 201

    sorted_pack = auth_client.patch(
        f"/v1/staff/packs/{pack['id']}/sort",
        headers=_headers(staff_token),
        json={"sort_order": 5},
    )
    assert sorted_pack.json()["sort_order"] == 5

    archived = auth_client.post(
        f"/v1/staff/packs/{pack['id']}/archive", headers=_headers(staff_token)
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_preset_round_trip_restores_packs_and_achievements(
    auth_client: TestClient, mailer: FakeEmailService, db: Session, storage: FakeStorage
) -> None:
    staff_token, _staff = _login(auth_client, mailer, db, "staff-preset", staff=True)
    slug = f"weather-{uuid.uuid4().hex[:6]}"
    pack = _create_official_pack_with_icons(auth_client, staff_token, slug=slug)
    auth_client.post(
        f"/v1/marketplace/staff/packs/{pack['id']}/publish", headers=_headers(staff_token)
    )
    pack_id = uuid.UUID(str(pack["id"]))

    rare_tag = IconSearchTag(slug=f"storm-{uuid.uuid4().hex[:4]}", labels={"en": "Storm"})
    db.add(rare_tag)
    db.flush()
    rain = db.scalar(
        select(CatalogIcon).where(CatalogIcon.pack_id == pack_id, CatalogIcon.slug == "rain")
    )
    assert rain is not None
    rain.search_tags = [rare_tag]
    rain.sort_order = -1  # rain before sun, not filename order

    achievement_slug = f"rainy_{uuid.uuid4().hex[:6]}"
    achievement = Achievement(
        slug=achievement_slug,
        category="collection",
        visibility="visible",
        status="published",
        labels={"en": "Rainy"},
        descriptions={"en": "Log a rainy day"},
        icon_type="emoji",
        icon="🌧️",
        criteria={"type": "entry_count", "count": 3},
    )
    db.add(achievement)
    db.flush()
    db.add(AchievementReward(achievement_id=achievement.id, kind="icon_pack", pack_id=pack_id))
    db.add(AchievementReward(achievement_id=achievement.id, kind="tokens", amount=20, sort_order=1))
    db.commit()

    # Only the achievement is selected; its reward pack must come along.
    response = auth_client.get(
        "/v1/staff/presets/export",
        params={"include_achievements": "true"},
        headers=_headers(staff_token),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert f"marketplace/{slug}/pack.json" in names
    assert f"marketplace/{slug}/sun.svg" in names
    assert "achievements/catalog.json" in names
    pack_meta = json.loads(archive.read(f"marketplace/{slug}/pack.json"))
    assert pack_meta["price_tokens"] == 40
    assert pack_meta["status"] == "published"
    assert pack_meta["granted"] is False
    catalog = json.loads(archive.read("achievements/catalog.json"))
    exported = next(item for item in catalog if item["slug"] == achievement_slug)
    assert {"kind": "icon_pack", "pack_slug": slug, "sort_order": 0} in exported["rewards"]

    # Simulate a fresh instance: drop what was exported, then import the archive.
    db.execute(delete(Achievement).where(Achievement.slug == achievement_slug))
    db.execute(delete(IconPack).where(IconPack.id == pack_id))
    db.execute(delete(IconSearchTag).where(IconSearchTag.id == rare_tag.id))
    db.commit()

    report = import_preset_archive(db, storage=storage, data=response.content)
    db.commit()
    assert slug in report.packs
    assert achievement_slug in report.achievements

    restored = db.scalar(select(IconPack).where(IconPack.slug == slug))
    assert restored is not None
    assert restored.price_tokens == 40
    assert restored.status == "published"
    assert restored.is_official is True
    assert [icon.slug for icon in restored.icons] == ["rain", "sun"]
    assert [tag.slug for tag in restored.icons[0].search_tags] == [rare_tag.slug]
    assert restored.icons[0].suggested_mood_scores == [4]

    restored_achievement = db.scalar(
        select(Achievement).where(Achievement.slug == achievement_slug)
    )
    assert restored_achievement is not None
    kinds = {
        (reward.kind, reward.pack_id, reward.amount) for reward in restored_achievement.rewards
    }
    assert kinds == {("icon_pack", restored.id, None), ("tokens", None, 20)}

    # Import is idempotent.
    again = import_preset_archive(db, storage=storage, data=response.content)
    db.commit()
    assert again.packs == report.packs
    assert db.scalar(select(IconPack).where(IconPack.slug == slug)).id == restored.id


def test_export_selected_packs_without_achievements(
    auth_client: TestClient, mailer: FakeEmailService, db: Session, storage: FakeStorage
) -> None:
    staff_token, _staff = _login(auth_client, mailer, db, "staff-select", staff=True)
    slug = f"weather-{uuid.uuid4().hex[:6]}"
    pack = _create_official_pack_with_icons(auth_client, staff_token, slug=slug)

    data, manifest = export_preset(
        db, storage=storage, pack_ids=[uuid.UUID(str(pack["id"]))], include_achievements=False
    )
    assert manifest["packs"] == [slug]
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "achievements/catalog.json" not in names
    # Drafts export as drafts so they stay hidden after import.
    meta = json.loads(zipfile.ZipFile(io.BytesIO(data)).read(f"marketplace/{slug}/pack.json"))
    assert meta["status"] == "draft"


def test_import_rejects_unsafe_archive(db: Session, storage: FakeStorage) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil/pack.json", "{}")
    from app.services.preset_service import PresetError

    with pytest.raises(PresetError):
        import_preset_archive(db, storage=storage, data=buffer.getvalue())
    with pytest.raises(PresetError):
        import_preset_archive(db, storage=storage, data=b"not a zip")


def test_staff_metrics_counts_sources_and_regular_writers(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.models.mood_entry import MoodEntry

    staff_token, staff = _login(auth_client, mailer, db, "metrics-staff", staff=True)
    _token, regular = _login(auth_client, mailer, db, "metrics-regular")
    _token, casual = _login(auth_client, mailer, db, "metrics-casual")
    regular.signup_source = "tiktok"
    casual.signup_source = "direct"
    now = datetime.now(UTC)

    def add_entries(user: User, days_ago: list[int], **extra: object) -> None:
        for days in days_ago:
            when = now - timedelta(days=days, hours=1)
            db.add(
                MoodEntry(
                    user_id=user.id,
                    recorded_at=when,
                    created_at=when,
                    score=3,
                    score_color="#22c55e",
                    **extra,
                )
            )

    add_entries(regular, [0, 0, 2, 4])  # three distinct days this week
    add_entries(casual, [1, 10])  # one day this week, one the week before
    add_entries(staff, [0, 1, 2])  # staff are left out
    db.commit()

    response = auth_client.get("/v1/staff/metrics", headers=_headers(staff_token))
    assert response.status_code == 200
    body = response.json()
    assert body["regular_min_days"] == 3

    sources = {row["source"]: row for row in body["sources"]}
    assert sources["tiktok"]["last_7_days"] >= 1
    assert sources["direct"]["total"] >= 1
    assert all(row["source"] for row in body["sources"])

    this_week, last_week = body["weeks"][0], body["weeks"][1]
    assert len(body["weeks"]) == 4
    assert this_week["active"] == 2
    assert this_week["regular"] == 1
    assert this_week["signups"] >= 2
    assert last_week["active"] == 1
    assert last_week["regular"] == 0

    user_token, _user = _login(auth_client, mailer, db, "metrics-guard")
    assert auth_client.get("/v1/staff/metrics", headers=_headers(user_token)).status_code == 403
