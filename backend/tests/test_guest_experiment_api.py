import pytest
from app.config import settings
from app.core.visitor_fingerprint import (
    canonical_fingerprint_payload,
    fingerprint_hash_from_payload,
)
from fastapi.testclient import TestClient


@pytest.fixture
def guest_experiment_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_guest_local_diary", True)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", 100)
    monkeypatch.setattr(settings, "feature_guest_local_diary_visitor_ids", "")


@pytest.fixture
def guest_experiment_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the control cohort; a developer .env may enable the experiment."""
    monkeypatch.setattr(settings, "feature_guest_local_diary", False)
    monkeypatch.setattr(settings, "feature_guest_local_diary_percent", 0)
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


def test_bootstrap_control_when_feature_off(
    auth_client: TestClient,
    guest_experiment_off: None,
) -> None:
    response = auth_client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    assert response.status_code == 200
    body = response.json()
    assert body["guest_local_diary"] is False
    assert body["cohort"] == "control"


def test_bootstrap_treatment_when_enabled(
    auth_client: TestClient,
    guest_experiment_on: None,
) -> None:
    response = auth_client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    assert response.status_code == 200
    body = response.json()
    assert body["guest_local_diary"] is True
    assert body["cohort"] == "treatment"
    assert settings.guest_visitor_cookie_name in response.cookies


def test_bootstrap_restores_visitor_by_fingerprint(
    auth_client: TestClient,
    guest_experiment_on: None,
) -> None:
    first = auth_client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    visitor_id = first.json()["visitor_id"]
    second = auth_client.post("/v1/features/bootstrap", json={"fingerprint": _fingerprint_body()})
    assert second.json()["visitor_id"] == visitor_id


def test_heartbeat_rejects_control(
    auth_client: TestClient,
    guest_experiment_off: None,
) -> None:
    bootstrap = auth_client.post(
        "/v1/features/bootstrap",
        json={"fingerprint": _fingerprint_body()},
    )
    visitor_id = bootstrap.json()["visitor_id"]
    heartbeat = auth_client.post(
        "/v1/guest/heartbeat",
        json={"visitor_id": visitor_id, "entry_count": 1},
    )
    assert heartbeat.status_code == 403


def test_heartbeat_accepts_treatment(
    auth_client: TestClient,
    guest_experiment_on: None,
) -> None:
    bootstrap = auth_client.post(
        "/v1/features/bootstrap",
        json={"fingerprint": _fingerprint_body()},
    )
    visitor_id = bootstrap.json()["visitor_id"]
    heartbeat = auth_client.post(
        "/v1/guest/heartbeat",
        json={"visitor_id": visitor_id, "entry_count": 3, "onboarding_completed": True},
    )
    assert heartbeat.status_code == 200


def test_fingerprint_hash_is_canonical() -> None:
    payload = canonical_fingerprint_payload(
        user_agent="TestAgent",
        accept_language="en",
        timezone="Europe/Minsk",
        screen_width=100,
        screen_height=200,
        screen_dpr=2,
        platform="Linux",
        max_touch_points=0,
    )
    first = fingerprint_hash_from_payload(payload)
    second = fingerprint_hash_from_payload(payload)
    assert first == second
    assert len(first) == 64
