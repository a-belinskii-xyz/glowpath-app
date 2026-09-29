"""Achievement catalog evaluation and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.core.achievements import AchievementStatus
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.goal import Goal
from app.models.user import User
from app.models.user_achievement import UserAchievement
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


@pytest.fixture(autouse=True)
def _enable_achievements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_achievements", True)
    monkeypatch.setattr(settings, "feature_achievements_percent", 100)
    monkeypatch.setattr(settings, "feature_achievements_emails", "")
    monkeypatch.setattr(settings, "feature_achievements_user_ids", "")
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


def _seed_minimal_catalog(db: Session) -> None:
    first = Achievement(
        slug=f"first_entry_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        visibility="visible",
        status=AchievementStatus.PUBLISHED.value,
        labels={"en": "First step", "ru": "Первый шаг"},
        descriptions={"en": "Log your first mood entry.", "ru": "Сделай первую запись."},
        icon_type="emoji",
        icon="🌱",
        criteria={"type": "entry_count", "count": 1},
        sort_order=10,
    )
    friday = Achievement(
        slug=f"friday_the_13th_{uuid.uuid4().hex[:8]}",
        category="secrets",
        visibility="secret",
        status=AchievementStatus.PUBLISHED.value,
        labels={"en": "Unlucky Friday", "ru": "Пятница 13"},
        descriptions={"en": "Check in on Friday the 13th.", "ru": "Отметься в пятницу 13-го."},
        icon_type="emoji",
        icon="👻",
        criteria={"type": "calendar_match", "weekday": 4, "day": 13},
        sort_order=40,
    )
    db.add_all([first, friday])
    db.flush()
    db.add(
        AchievementReward(
            achievement_id=first.id,
            kind="tokens",
            amount=10,
            sort_order=10,
        )
    )
    db.add(
        AchievementReward(
            achievement_id=friday.id,
            kind="tokens",
            amount=30,
            sort_order=10,
        )
    )
    db.commit()
    first.slug = "first_entry_test"
    friday.slug = "friday_the_13th_test"
    # Keep unique slugs from construction — store for assertions via category
    db.commit()


def test_list_hides_secret_details(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    _seed_minimal_catalog(db)
    token = register_verify_and_login(auth_client, mailer, f"ach-list-{uuid.uuid4()}@example.com")
    listed = auth_client.get("/v1/achievements", headers=_auth_headers(token))
    assert listed.status_code == 200, listed.text
    secrets = [item for item in listed.json()["items"] if item["visibility"] == "secret"]
    assert secrets
    for secret in secrets:
        if not secret["unlocked"]:
            assert secret.get("slug") is None
            assert secret.get("name") is None
            assert secret.get("description") is None
            assert secret.get("rewards") in (None, [])


def test_first_entry_unlocks_and_grants_tokens(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    first = Achievement(
        slug=f"first_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        visibility="visible",
        status=AchievementStatus.PUBLISHED.value,
        labels={"en": "First step", "ru": "Первый шаг"},
        descriptions={"en": "First", "ru": "Первый"},
        icon_type="emoji",
        icon="🌱",
        criteria={"type": "entry_count", "count": 1},
        sort_order=10,
    )
    db.add(first)
    db.flush()
    db.add(
        AchievementReward(
            achievement_id=first.id,
            kind="tokens",
            amount=10,
            sort_order=10,
        )
    )
    db.commit()

    token = register_verify_and_login(auth_client, mailer, f"ach-first-{uuid.uuid4()}@example.com")
    user = _user_from_token(db, auth_client, token)
    user.onboarding_completed_at = datetime.now(UTC)
    user.timezone = "UTC"
    db.commit()

    create = auth_client.post(
        "/v1/mood-entries",
        headers=_auth_headers(token),
        json={
            "score": 4,
            "recorded_at": "2026-01-15T12:00:00+00:00",
            "note": None,
            "tag_ids": [],
            "goal_ids": [],
        },
    )
    assert create.status_code == 201, create.text
    unlocked = create.json().get("unlocked_achievements") or []
    assert any(item.get("id") == str(first.id) for item in unlocked)
    unlocked_item = next(item for item in unlocked if item.get("id") == str(first.id))
    assert unlocked_item.get("unlocked_by_entry_id") == create.json()["id"]
    assert unlocked_item.get("unlock_percent") is not None

    wallet = auth_client.get("/v1/wallet", headers=_auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] >= 10

    listed = auth_client.get("/v1/achievements", headers=_auth_headers(token))
    assert listed.status_code == 200
    card = next(item for item in listed.json()["items"] if item["id"] == str(first.id))
    assert card["unlocked_by_entry_id"] == create.json()["id"]
    assert isinstance(card["unlock_percent"], int | float)

    progress = db.scalar(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == first.id,
        )
    )
    assert progress is not None
    assert progress.unlocked_at is not None
    assert progress.unlocked_by_entry_id is not None
    assert str(progress.unlocked_by_entry_id) == create.json()["id"]


def test_friday_the_13th_in_user_timezone(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    friday = Achievement(
        slug=f"fri_{uuid.uuid4().hex[:8]}",
        category="secrets",
        visibility="secret",
        status=AchievementStatus.PUBLISHED.value,
        labels={"en": "Unlucky Friday", "ru": "Пятница 13"},
        descriptions={"en": "Friday 13", "ru": "Пятница 13"},
        icon_type="emoji",
        icon="👻",
        criteria={"type": "calendar_match", "weekday": 4, "day": 13},
        sort_order=40,
    )
    db.add(friday)
    db.flush()
    db.add(
        AchievementReward(
            achievement_id=friday.id,
            kind="tokens",
            amount=30,
            sort_order=10,
        )
    )
    db.commit()

    token = register_verify_and_login(auth_client, mailer, f"ach-fri-{uuid.uuid4()}@example.com")
    user = _user_from_token(db, auth_client, token)
    user.onboarding_completed_at = datetime.now(UTC)
    user.timezone = "Europe/Minsk"
    db.commit()

    create = auth_client.post(
        "/v1/mood-entries",
        headers=_auth_headers(token),
        json={
            "score": 3,
            "recorded_at": "2026-02-13T07:00:00+00:00",
            "note": None,
            "tag_ids": [],
            "goal_ids": [],
        },
    )
    assert create.status_code == 201, create.text
    unlocked = create.json().get("unlocked_achievements") or []
    assert any(item.get("id") == str(friday.id) for item in unlocked)

    listed = auth_client.get("/v1/achievements", headers=_auth_headers(token))
    assert listed.status_code == 200
    secret = next(item for item in listed.json()["items"] if item["id"] == str(friday.id))
    assert secret["unlocked"] is True
    assert secret["slug"] == friday.slug
    assert secret["name"]


def _publish(
    db: Session,
    *,
    slug: str,
    category: str,
    criteria: dict,
    visibility: str = "visible",
    amount: int = 10,
) -> Achievement:
    achievement = Achievement(
        slug=slug,
        category=category,
        visibility=visibility,
        status=AchievementStatus.PUBLISHED.value,
        labels={"en": slug, "ru": slug},
        descriptions={"en": slug, "ru": slug},
        icon_type="emoji",
        icon="🏅",
        criteria=criteria,
        sort_order=500,
    )
    db.add(achievement)
    db.flush()
    db.add(
        AchievementReward(
            achievement_id=achievement.id,
            kind="tokens",
            amount=amount,
            sort_order=10,
        )
    )
    db.commit()
    return achievement


def test_catalog_json_uses_known_criteria_and_unique_slugs() -> None:
    from pathlib import Path

    from app.core.achievements import (
        ACHIEVEMENT_CATEGORIES,
        ACHIEVEMENT_REWARD_KINDS,
        CRITERIA_TYPES,
    )

    path = Path(__file__).resolve().parents[1] / "app" / "data" / "achievements" / "catalog.json"
    import json

    items = json.loads(path.read_text(encoding="utf-8"))
    slugs = [item["slug"] for item in items]
    assert len(slugs) == len(set(slugs))
    icons = [item["icon"]["value"] for item in items]
    assert len(icons) == len(set(icons))
    for item in items:
        assert item["category"] in ACHIEVEMENT_CATEGORIES
        assert item["criteria"]["type"] in CRITERIA_TYPES
        assert "en" in item["labels"] and "ru" in item["labels"]
        assert "en" in item["descriptions"] and "ru" in item["descriptions"]
        if item["visibility"] == "secret":
            assert item["category"] == "secrets"
        for reward in item["rewards"]:
            assert reward["kind"] in ACHIEVEMENT_REWARD_KINDS


def test_note_and_favorite_unlock(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    note = _publish(
        db,
        slug=f"note_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        criteria={"type": "entries_with_note", "count": 1},
    )
    fav = _publish(
        db,
        slug=f"fav_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        criteria={"type": "favorite_count", "count": 1},
    )
    token = register_verify_and_login(auth_client, mailer, f"ach-note-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)

    create = auth_client.post(
        "/v1/mood-entries",
        headers=headers,
        json={
            "score": 4,
            "recorded_at": "2026-03-01T12:00:00+00:00",
            "note": "hello",
            "tag_ids": [],
            "goal_ids": [],
        },
    )
    assert create.status_code == 201, create.text
    unlocked_ids = {item["id"] for item in create.json().get("unlocked_achievements") or []}
    assert str(note.id) in unlocked_ids
    assert str(fav.id) not in unlocked_ids

    patched = auth_client.patch(
        f"/v1/mood-entries/{create.json()['id']}",
        headers=headers,
        json={"is_favorite": True},
    )
    assert patched.status_code == 200, patched.text
    fav_unlocked = {item["id"] for item in patched.json().get("unlocked_achievements") or []}
    assert str(fav.id) in fav_unlocked


def test_photo_attachment_unlocks(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    import io

    photo = _publish(
        db,
        slug=f"photo_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        criteria={"type": "attachment_count", "kind": "photo", "count": 1},
    )
    token = register_verify_and_login(auth_client, mailer, f"ach-photo-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)
    created = auth_client.post(
        "/v1/mood-entries",
        headers=headers,
        json={
            "score": 3,
            "recorded_at": "2026-03-02T12:00:00+00:00",
            "note": None,
            "tag_ids": [],
            "goal_ids": [],
        },
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]
    upload = auth_client.post(
        f"/v1/mood-entries/{entry_id}/attachments",
        headers=headers,
        data={"kind": "photo"},
        files={"file": ("shot.jpg", io.BytesIO(b"fake-photo"), "image/jpeg")},
    )
    assert upload.status_code == 201, upload.text

    listed = auth_client.get("/v1/achievements", headers=headers)
    card = next(item for item in listed.json()["items"] if item["id"] == str(photo.id))
    assert card["unlocked"] is True


def test_custom_goal_unlocks_not_defaults(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    first_goal = _publish(
        db,
        slug=f"goal_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        criteria={"type": "goal_created_count", "count": 1},
    )
    token = register_verify_and_login(auth_client, mailer, f"ach-goal-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)

    # The criterion tells defaults from custom goals by created_at > user.created_at.
    # Tests run in one DB transaction where now() is frozen, so move the registration
    # (user + provisioned default goals) into the past like a real earlier request.
    me = auth_client.get("/v1/auth/me", headers=headers).json()
    user_id = uuid.UUID(me["id"])
    earlier = timedelta(minutes=5)
    db.execute(update(User).where(User.id == user_id).values(created_at=User.created_at - earlier))
    db.execute(
        update(Goal).where(Goal.user_id == user_id).values(created_at=Goal.created_at - earlier)
    )
    db.commit()

    listed = auth_client.get("/v1/achievements", headers=headers)
    card = next(item for item in listed.json()["items"] if item["id"] == str(first_goal.id))
    assert card["unlocked"] is False

    created = auth_client.post(
        "/v1/goals",
        headers=headers,
        json={
            "labels": {"en": "Custom walk"},
            "times_per_week": 3,
            "starts_on": "2026-03-01",
            "show_on_entry": False,
        },
    )
    assert created.status_code == 201, created.text

    listed = auth_client.get("/v1/achievements", headers=headers)
    card = next(item for item in listed.json()["items"] if item["id"] == str(first_goal.id))
    assert card["unlocked"] is True


def test_telegram_source_and_night_owl(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    telegram = _publish(
        db,
        slug=f"tg_{uuid.uuid4().hex[:8]}",
        category="getting_started",
        criteria={"type": "source_prefix", "prefix": "telegram", "count": 1},
    )
    owl = _publish(
        db,
        slug=f"owl_{uuid.uuid4().hex[:8]}",
        category="secrets",
        visibility="secret",
        criteria={"type": "local_hour_range", "hour_from": 23, "hour_to": 5, "count": 1},
    )
    token = register_verify_and_login(auth_client, mailer, f"ach-src-{uuid.uuid4()}@example.com")
    user = _user_from_token(db, auth_client, token)
    user.timezone = "UTC"
    db.commit()
    headers = _auth_headers(token)

    create = auth_client.post(
        "/v1/mood-entries",
        headers=headers,
        json={
            "score": 2,
            "recorded_at": "2026-03-03T23:15:00+00:00",
            "note": None,
            "tag_ids": [],
            "goal_ids": [],
            "source": "telegram:bot",
        },
    )
    assert create.status_code == 201, create.text
    unlocked_ids = {item["id"] for item in create.json().get("unlocked_achievements") or []}
    assert str(telegram.id) in unlocked_ids
    assert str(owl.id) in unlocked_ids


def test_distinct_scores_and_checkin(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    shades = _publish(
        db,
        slug=f"shades_{uuid.uuid4().hex[:8]}",
        category="collection",
        criteria={"type": "distinct_scores", "count": 5},
    )
    token = register_verify_and_login(auth_client, mailer, f"ach-scores-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)
    for score, day in enumerate((1, 2, 3, 4, 5), start=1):
        response = auth_client.post(
            "/v1/mood-entries",
            headers=headers,
            json={
                "score": score,
                "recorded_at": f"2026-03-0{day}T12:00:00+00:00",
                "note": None,
                "tag_ids": [],
                "goal_ids": [],
            },
        )
        assert response.status_code == 201, response.text

    listed = auth_client.get("/v1/achievements", headers=headers)
    card = next(item for item in listed.json()["items"] if item["id"] == str(shades.id))
    assert card["unlocked"] is True
