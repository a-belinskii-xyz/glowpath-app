"""Entries written from the «Моё» screen carry their own marker (GP-46)."""

from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, register_verify_and_login


def test_win_entries_are_marked_and_filtered(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, "wins@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    base = {"score": 4, "recorded_at": "2026-10-10T12:00:00+03:00", "tag_ids": []}

    win = auth_client.post("/v1/mood-entries", json=base | {"is_win": True}, headers=headers)
    assert win.status_code == 201, win.text
    assert win.json()["is_win"] is True
    assert win.json()["is_favorite"] is False
    plain = auth_client.post("/v1/mood-entries", json=base, headers=headers)
    assert plain.json()["is_win"] is False

    wins = auth_client.get("/v1/mood-entries", params={"is_win": True}, headers=headers)
    assert [item["id"] for item in wins.json()["items"]] == [win.json()["id"]]
    everything = auth_client.get("/v1/mood-entries", headers=headers)
    assert len(everything.json()["items"]) == 2
