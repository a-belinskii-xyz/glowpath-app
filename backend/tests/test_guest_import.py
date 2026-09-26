import uuid

import pytest
from fastapi.testclient import TestClient

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


def test_guest_import_rejected_for_existing_login_without_pending(
    client: TestClient,
    auth_client: TestClient,
    mailer: FakeEmailService,
    guest_experiment_on: None,
) -> None:
    existing_email = f"existing-{uuid.uuid4()}@example.com"
    register_verify_and_login(auth_client, mailer, existing_email)

    bootstrap = client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    visitor_id = bootstrap.json()["visitor_id"]

    login = auth_client.post(
        "/v1/auth/login",
        json={
            "email": existing_email,
            "password": "password123",
            "visitor_id": visitor_id,
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "meta": {"onboarding_completed": False},
        "tag_groups": [],
        "tags": [],
        "goals": [],
        "note_templates": [],
        "entries": [
            {
                "score": 3,
                "recorded_at": "2026-08-28T11:00:00+03:00",
                "note": "Should not import",
                "is_favorite": False,
                "tag_ids": [],
                "goal_ids": [],
                "goal_progress": [],
            }
        ],
    }
    response = auth_client.post(
        "/v1/guest/import",
        json={"visitor_id": visitor_id, "payload": payload},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
