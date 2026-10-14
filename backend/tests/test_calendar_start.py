"""Month calendar that starts from the user's own start (GP-45)."""

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _today(client: TestClient, token: str) -> date:
    me = client.get("/v1/auth/me", headers=_headers(token)).json()
    return datetime.now(ZoneInfo(me["timezone"])).date()


def test_calendar_start_defaults_toggle_and_reset(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"cal-start-{uuid.uuid4()}@example.com")
    headers = _headers(token)

    prefs = auth_client.get("/v1/mood-preferences", headers=headers).json()
    assert prefs["calendar_from_start"] is False
    assert prefs["calendar_start_on"] is None
    assert prefs["first_entry_on"] is None

    entry = auth_client.post(
        "/v1/mood-entries",
        json={"score": 4, "recorded_at": "2026-03-12T12:00:00+03:00", "tag_ids": []},
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    prefs = auth_client.get("/v1/mood-preferences", headers=headers).json()
    assert prefs["first_entry_on"] == "2026-03-12"

    on = auth_client.patch(
        "/v1/mood-preferences",
        json={"calendar_from_start": True, "calendar_start_on": "2026-03-20"},
        headers=headers,
    )
    assert on.status_code == 200, on.text
    assert on.json()["calendar_from_start"] is True
    assert on.json()["calendar_start_on"] == "2026-03-20"

    # Other settings leave the start date alone.
    streak = auth_client.patch("/v1/mood-preferences", json={"show_streak": False}, headers=headers)
    assert streak.json()["calendar_start_on"] == "2026-03-20"

    reset = auth_client.patch(
        "/v1/mood-preferences", json={"calendar_start_on": None}, headers=headers
    )
    assert reset.status_code == 200
    assert reset.json()["calendar_start_on"] is None
    assert reset.json()["calendar_from_start"] is True


def test_calendar_start_cannot_be_in_the_future(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"cal-future-{uuid.uuid4()}@example.com")
    today = _today(auth_client, token)

    ok = auth_client.patch(
        "/v1/mood-preferences",
        json={"calendar_start_on": today.isoformat()},
        headers=_headers(token),
    )
    assert ok.status_code == 200
    future = auth_client.patch(
        "/v1/mood-preferences",
        json={"calendar_start_on": (today + timedelta(days=2)).isoformat()},
        headers=_headers(token),
    )
    assert future.status_code == 400
    assert future.json()["detail"]["code"] == "calendar_start_in_future"
