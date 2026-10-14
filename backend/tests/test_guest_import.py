import uuid

import pytest
from app.services.telegram_auth_service import login_or_create_telegram_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import (
    FakeEmailService,
    extract_token_from_email,
    register_verify_and_login,
)


@pytest.fixture
def guest_experiment_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "feature_guest_local_diary", True)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", 100)
    monkeypatch.setattr(settings, "feature_guest_local_diary_visitor_ids", "")


def _fingerprint_body() -> dict[str, object]:
    return {
        "timezone": "Europe/Minsk",
        "screen_width": 1280,
        "screen_height": 800,
        "screen_dpr": 2,
        "platform": "Linux",
        "max_touch_points": 0,
    }


def test_guest_import_only_for_new_registration(
    client: TestClient,
    auth_client: TestClient,
    mailer: FakeEmailService,
    guest_experiment_on: None,
) -> None:
    bootstrap = client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    visitor_id = bootstrap.json()["visitor_id"]

    email = f"guest-import-{uuid.uuid4()}@example.com"
    register = auth_client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "password_confirm": "password123",
            "timezone": "Europe/Minsk",
            "visitor_id": visitor_id,
        },
    )
    assert register.status_code == 201

    verify_token = extract_token_from_email(mailer.outbox[-1].body)
    assert auth_client.get(f"/v1/auth/verify-email?token={verify_token}").status_code == 200
    login = auth_client.post("/v1/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "meta": {"onboarding_completed": True},
        "tag_groups": [],
        "tags": [],
        "goals": [],
        "note_templates": [],
        "entries": [
            {
                "score": 4,
                "recorded_at": "2026-08-28T10:00:00+03:00",
                "note": "Guest note",
                "is_favorite": False,
                "tag_ids": [],
                "goal_ids": [],
                "goal_progress": [],
            }
        ],
    }
    imported = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": payload},
        headers=headers,
    )
    assert imported.status_code == 200
    assert imported.json()["imported_entries"] == 1

    duplicate = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": payload},
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["skipped"] is True


def _guest_payload(note: str) -> dict[str, object]:
    return {
        "meta": {"onboarding_completed": True},
        "tag_groups": [],
        "tags": [],
        "goals": [],
        "note_templates": [],
        "mood_preferences": {"show_streak": False},
        "entries": [
            {
                "score": 3,
                "recorded_at": "2026-08-28T11:00:00+03:00",
                "note": note,
                "is_favorite": False,
                "tag_ids": [],
                "goal_ids": [],
                "goal_progress": [],
            }
        ],
    }


def test_guest_import_into_existing_account_after_login(
    client: TestClient,
    auth_client: TestClient,
    mailer: FakeEmailService,
    guest_experiment_on: None,
) -> None:
    existing_email = f"existing-{uuid.uuid4()}@example.com"
    first_token = register_verify_and_login(auth_client, mailer, existing_email)
    first_headers = {"Authorization": f"Bearer {first_token}"}
    own_entry = auth_client.post(
        "/v1/mood-entries",
        json={"score": 5, "recorded_at": "2026-08-27T10:00:00+03:00"},
        headers=first_headers,
    )
    assert own_entry.status_code == 201
    prefs_before = auth_client.get("/v1/mood-preferences", headers=first_headers).json()

    bootstrap = client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    visitor_id = bootstrap.json()["visitor_id"]

    # Before signing in from the guest's browser there is nothing to import into.
    rejected = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": _guest_payload("Too early")},
        headers=first_headers,
    )
    assert rejected.status_code == 409

    login = auth_client.post(
        "/v1/auth/login",
        json={"email": existing_email, "password": "password123", "visitor_id": visitor_id},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    imported = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": _guest_payload("From the guest diary")},
        headers=headers,
    )
    assert imported.status_code == 200
    assert imported.json() == {"imported_entries": 1, "skipped": False}

    duplicate = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": _guest_payload("From the guest diary")},
        headers=headers,
    )
    assert duplicate.json()["skipped"] is True

    entries = auth_client.get("/v1/mood-entries", headers=headers).json()
    items = entries["items"] if isinstance(entries, dict) else entries
    assert sorted(item["note"] or "" for item in items) == ["", "From the guest diary"]
    # The account had its own entries, so its settings stay as they were.
    prefs_after = auth_client.get("/v1/mood-preferences", headers=headers).json()
    assert prefs_after["show_streak"] == prefs_before["show_streak"]


def test_guest_import_into_existing_telegram_account(
    client: TestClient,
    auth_client: TestClient,
    db: Session,
    guest_experiment_on: None,
) -> None:
    telegram_user_id = 900_000 + uuid.uuid4().int % 90_000
    login_or_create_telegram_user(
        db, telegram_user_id=telegram_user_id, timezone="Europe/Minsk", locale="ru"
    )

    bootstrap = client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    visitor_id = bootstrap.json()["visitor_id"]

    tokens = login_or_create_telegram_user(
        db,
        telegram_user_id=telegram_user_id,
        timezone="Europe/Minsk",
        locale="ru",
        visitor_id=uuid.UUID(visitor_id),
    )
    assert tokens.user_created is False

    imported = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": _guest_payload("Before Telegram")},
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert imported.status_code == 200
    assert imported.json()["imported_entries"] == 1


def test_guest_import_carries_goal_checkins(
    client: TestClient,
    auth_client: TestClient,
    mailer: FakeEmailService,
    guest_experiment_on: None,
) -> None:
    visitor_id = client.post(
        "/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()}
    ).json()["visitor_id"]
    email = f"guest-checkin-{uuid.uuid4()}@example.com"
    register = auth_client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "password_confirm": "password123",
            "timezone": "Europe/Minsk",
            "visitor_id": visitor_id,
        },
    )
    assert register.status_code == 201
    verify_token = extract_token_from_email(mailer.outbox[-1].body)
    assert auth_client.get(f"/v1/auth/verify-email?token={verify_token}").status_code == 200
    login = auth_client.post("/v1/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    goal = {
        "local_id": "local-goal",
        "slug": "walk_outside",
        "labels": {"en": "Walk outside"},
        "times_per_week": 7,
        "starts_on": "2026-08-01",
        "partial_label": "five minutes at the door",
        "checkins": {"2026-08-27": "partial", "2026-08-28": "full", "bad": "full"},
    }
    payload = {
        "meta": {"onboarding_completed": True},
        "tag_groups": [],
        "tags": [],
        "goals": [goal],
        "note_templates": [],
        "mood_preferences": {"calendar_from_start": True, "calendar_start_on": "2026-08-12"},
        "entries": [],
    }
    imported = auth_client.post(
        "/v1/guest/import", json={"visitor_id": visitor_id, "payload": payload}, headers=headers
    )
    assert imported.status_code == 200, imported.text

    listed = auth_client.get("/v1/goals", params={"progress_on": "2026-08-28"}, headers=headers)
    walk = next(item for item in listed.json()["items"] if item["slug"] == "walk_outside")
    assert walk["partial_label"] == "five minutes at the door"
    assert walk["week_marks"] == [
        {"date": "2026-08-27", "level": "partial", "amount": None},
        {"date": "2026-08-28", "level": "full", "amount": None},
    ]
    # GP-45: the calendar start setting comes along too.
    prefs = auth_client.get("/v1/mood-preferences", headers=headers).json()
    assert prefs["calendar_from_start"] is True
    assert prefs["calendar_start_on"] == "2026-08-12"
