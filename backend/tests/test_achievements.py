"""Achievement catalog evaluation and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.config import settings
from app.core.achievements import AchievementStatus
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.user import User
from app.models.user_achievement import UserAchievement
from fastapi.testclient import TestClient
from sqlalchemy import select
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

    wallet = auth_client.get("/v1/wallet", headers=_auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] >= 10

    progress = db.scalar(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == first.id,
        )
    )
    assert progress is not None
    assert progress.unlocked_at is not None


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
