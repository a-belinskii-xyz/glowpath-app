"""Icon marketplace integration tests."""

from __future__ import annotations

import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.core.marketplace import PackStatus
from app.models.user import User
from app.services.marketplace_seed import seed_default_search_tags, seed_essentials_pack
from app.services.marketplace_service import (
    create_studio_pack,
    publish_pack,
    upload_studio_icon,
)
from app.services.storage import FakeStorage
from app.services.wallet_service import grant_tokens
from tests.conftest import FakeEmailService, register_verify_and_login


@pytest.fixture(autouse=True)
def _enable_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_icon_marketplace", True)
    monkeypatch.setattr(settings, "feature_icon_marketplace_percent", 100)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user_from_token(db: Session, auth_client: TestClient, token: str) -> User:
    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    user = db.get(User, uuid.UUID(me.json()["id"]))
    assert user is not None
    return user


def _make_published_paid_pack(
    db: Session,
    storage: FakeStorage,
    *,
    author: User,
    staff: User,
    price: int = 50,
    tag_slugs: list[str] | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    seed_default_search_tags(db)
    pack = create_studio_pack(
        db,
        user=author,
        labels={
            "name": {"en": "Fox Pack", "ru": "Лисы"},
            "description": {"en": "Cute foxes", "ru": "Милые лисы"},
        },
        slug=f"fox-{uuid.uuid4().hex[:8]}",
        price_tokens=price,
    )
    icon = upload_studio_icon(
        db,
        user=author,
        pack_id=pack.id,
        storage=storage,
        data=b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        content_type="image/svg+xml",
        original_name="fox.svg",
        labels={"en": "Happy fox", "ru": "Весёлый лис"},
        suggested_colors=["#f97316", "#f59e0b"],
        suggested_mood_scores=[4, 5],
        search_tag_slugs=tag_slugs or ["joy", "animals"],
    )
    pack.status = PackStatus.PENDING_REVIEW.value
    publish_pack(db, staff=staff, pack_id=pack.id)
    db.commit()
    return pack.id, icon.id


def test_search_tags_and_icon_filter(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"mp-search-{uuid.uuid4()}@example.com")
    user = _user_from_token(db, auth_client, token)
    user.is_staff = True
    db.commit()

    author_token = register_verify_and_login(
        auth_client, mailer, f"mp-author-{uuid.uuid4()}@example.com"
    )
    author = _user_from_token(db, auth_client, author_token)
    pack_id, icon_id = _make_published_paid_pack(
        db, storage, author=author, staff=user, price=0, tag_slugs=["sport", "energy"]
    )

    tags = auth_client.get("/v1/marketplace/search-tags", headers=_auth_headers(token))
    assert tags.status_code == 200
    slugs = {item["slug"] for item in tags.json()["items"]}
    assert "sport" in slugs
    assert "joy" in slugs

    found = auth_client.get(
        "/v1/marketplace/icons",
        params={"tag": "sport", "suggested_mood": 5},
        headers=_auth_headers(token),
    )
    assert found.status_code == 200
    ids = [item["id"] for item in found.json()["items"]]
    assert str(icon_id) in ids

    packs = auth_client.get(
        "/v1/marketplace/packs",
        params={"tag": "sport"},
        headers=_auth_headers(token),
    )
    assert packs.status_code == 200
    assert any(item["id"] == str(pack_id) for item in packs.json()["items"])


def test_unlock_requires_tokens_and_is_idempotent(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    staff_token = register_verify_and_login(
        auth_client, mailer, f"mp-staff-{uuid.uuid4()}@example.com"
    )
    staff = _user_from_token(db, auth_client, staff_token)
    staff.is_staff = True
    db.commit()

    author_token = register_verify_and_login(
        auth_client, mailer, f"mp-author2-{uuid.uuid4()}@example.com"
    )
    author = _user_from_token(db, auth_client, author_token)
    pack_id, _icon_id = _make_published_paid_pack(
        db, storage, author=author, staff=staff, price=40
    )

    buyer_token = register_verify_and_login(
        auth_client, mailer, f"mp-buyer-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(buyer_token)

    failed = auth_client.post(f"/v1/marketplace/packs/{pack_id}/unlock", headers=headers)
    assert failed.status_code == 402
    assert failed.json()["detail"]["code"] == "insufficient_tokens"

    buyer = _user_from_token(db, auth_client, buyer_token)
    grant_tokens(db, user_id=buyer.id, amount=100, created_by=staff.id)
    db.commit()

    wallet = auth_client.get("/v1/wallet", headers=headers)
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 100

    unlocked = auth_client.post(f"/v1/marketplace/packs/{pack_id}/unlock", headers=headers)
    assert unlocked.status_code == 200
    assert unlocked.json()["pack"]["unlocked"] is True

    wallet_after = auth_client.get("/v1/wallet", headers=headers)
    assert wallet_after.json()["balance"] == 60

    again = auth_client.post(f"/v1/marketplace/packs/{pack_id}/unlock", headers=headers)
    assert again.status_code == 200
    assert auth_client.get("/v1/wallet", headers=headers).json()["balance"] == 60


def test_catalog_assign_requires_unlock(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    staff_token = register_verify_and_login(
        auth_client, mailer, f"mp-staff3-{uuid.uuid4()}@example.com"
    )
    staff = _user_from_token(db, auth_client, staff_token)
    staff.is_staff = True
    db.commit()

    author_token = register_verify_and_login(
        auth_client, mailer, f"mp-author3-{uuid.uuid4()}@example.com"
    )
    author = _user_from_token(db, auth_client, author_token)
    pack_id, icon_id = _make_published_paid_pack(
        db, storage, author=author, staff=staff, price=10
    )

    buyer_token = register_verify_and_login(
        auth_client, mailer, f"mp-buyer3-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(buyer_token)

    denied = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={"scores": {"4": {"icon_type": "catalog", "icon": str(icon_id)}}},
    )
    assert denied.status_code == 400
    assert denied.json()["detail"]["code"] == "catalog_icon_not_assignable"

    buyer = _user_from_token(db, auth_client, buyer_token)
    grant_tokens(db, user_id=buyer.id, amount=10, created_by=staff.id)
    db.commit()
    assert (
        auth_client.post(f"/v1/marketplace/packs/{pack_id}/unlock", headers=headers).status_code
        == 200
    )

    allowed = auth_client.patch(
        "/v1/mood-preferences",
        headers=headers,
        json={
            "scores": {
                "4": {
                    "icon_type": "catalog",
                    "icon": str(icon_id),
                    "color": "#f97316",
                }
            }
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["scores"]["4"]["icon_type"] == "catalog"
    assert allowed.json()["scores"]["4"]["icon"] == str(icon_id)


def test_free_essentials_assignable_without_unlock(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"mp-essentials-{uuid.uuid4()}@example.com"
    )
    pack = seed_essentials_pack(db, storage=storage)
    db.commit()
    icon = pack.icons[0]

    response = auth_client.patch(
        "/v1/mood-preferences",
        headers=_auth_headers(token),
        json={"scores": {"3": {"icon_type": "catalog", "icon": str(icon.id)}}},
    )
    assert response.status_code == 200
    assert response.json()["scores"]["3"]["icon_type"] == "catalog"

    listed = auth_client.get("/v1/marketplace/packs", headers=_auth_headers(token))
    assert listed.status_code == 200
    essentials = next(item for item in listed.json()["items"] if item["slug"] == "essentials")
    assert essentials["price_tokens"] == 0
    assert essentials["unlocked"] is True
    assert essentials["is_official"] is True


def test_moderation_submit_publish_reject(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    storage: FakeStorage,
) -> None:
    staff_token = register_verify_and_login(
        auth_client, mailer, f"mp-mod-staff-{uuid.uuid4()}@example.com"
    )
    staff = _user_from_token(db, auth_client, staff_token)
    staff.is_staff = True
    db.commit()

    author_token = register_verify_and_login(
        auth_client, mailer, f"mp-mod-author-{uuid.uuid4()}@example.com"
    )
    author_headers = _auth_headers(author_token)
    staff_headers = _auth_headers(staff_token)

    seed_default_search_tags(db)
    db.commit()

    created = auth_client.post(
        "/v1/marketplace/studio/packs",
        headers=author_headers,
        json={
            "labels": {
                "name": {"en": "Draft Pack", "ru": "Черновик"},
                "description": {"en": "WIP", "ru": "В работе"},
            },
            "price_tokens": 5,
        },
    )
    assert created.status_code == 201
    pack_id = created.json()["id"]

    upload = auth_client.post(
        f"/v1/marketplace/studio/packs/{pack_id}/icons",
        headers=author_headers,
        files={"file": ("fox.png", io.BytesIO(b"png-bytes"), "image/png")},
        data={
            "labels": json.dumps({"en": "Fox", "ru": "Лис"}),
            "suggested_colors": json.dumps(["#f97316"]),
            "suggested_mood_scores": json.dumps([5]),
            "search_tag_slugs": json.dumps(["animals"]),
        },
    )
    assert upload.status_code == 201

    submitted = auth_client.post(
        f"/v1/marketplace/studio/packs/{pack_id}/submit",
        headers=author_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_review"

    pending = auth_client.get(
        "/v1/marketplace/staff/packs",
        params={"status": "pending_review"},
        headers=staff_headers,
    )
    assert pending.status_code == 200
    assert any(item["id"] == pack_id for item in pending.json()["items"])

    published = auth_client.post(
        f"/v1/marketplace/staff/packs/{pack_id}/publish",
        headers=staff_headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    rejected = auth_client.post(
        f"/v1/marketplace/staff/packs/{pack_id}/reject",
        headers=staff_headers,
        json={"note": "needs polish"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["moderation_note"] == "needs polish"


def test_staff_grant_tokens(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    staff_token = register_verify_and_login(
        auth_client, mailer, f"mp-grant-staff-{uuid.uuid4()}@example.com"
    )
    staff = _user_from_token(db, auth_client, staff_token)
    staff.is_staff = True
    db.commit()

    user_token = register_verify_and_login(
        auth_client, mailer, f"mp-grant-user-{uuid.uuid4()}@example.com"
    )
    user = _user_from_token(db, auth_client, user_token)

    grant = auth_client.post(
        "/v1/wallet/staff/grants",
        headers=_auth_headers(staff_token),
        json={"user_id": str(user.id), "amount": 25, "note": "welcome"},
    )
    assert grant.status_code == 200
    assert grant.json()["balance"] == 25

    wallet = auth_client.get("/v1/wallet", headers=_auth_headers(user_token))
    assert wallet.json()["balance"] == 25

    ledger = auth_client.get("/v1/wallet/ledger", headers=_auth_headers(user_token))
    assert ledger.status_code == 200
    assert ledger.json()["items"][0]["kind"] == "grant"
    assert ledger.json()["items"][0]["delta"] == 25


def test_marketplace_feature_flag_blocks_access(
    auth_client: TestClient,
    mailer: FakeEmailService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "feature_icon_marketplace", False)
    token = register_verify_and_login(
        auth_client, mailer, f"mp-flag-{uuid.uuid4()}@example.com"
    )
    response = auth_client.get("/v1/marketplace/packs", headers=_auth_headers(token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "marketplace_disabled"
