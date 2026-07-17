import io
import uuid

from fastapi.testclient import TestClient

from tests.conftest import FakeEmailService, FakeStorage, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _first_goal_id(auth_client: TestClient, headers: dict[str, str]) -> str:
    listed = auth_client.get("/v1/goals", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items
    return items[0]["id"]


def test_goal_icon_upload_list_select_delete(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"goal-icon-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)
    goal_id = _first_goal_id(auth_client, headers)

    upload = auth_client.post(
        f"/v1/goals/{goal_id}/icons",
        headers=headers,
        files={"file": ("icon.png", io.BytesIO(b"png-bytes"), "image/png")},
    )
    assert upload.status_code == 201
    body = upload.json()
    icon_id = body["id"]
    assert body["goal_id"] == goal_id
    assert body["goal"]["icon_type"] == "upload"
    assert body["goal"]["icon"] == icon_id
    assert len(storage._objects) == 1

    download = auth_client.get(f"/v1/goals/icons/id/{icon_id}", headers=headers)
    assert download.status_code == 200
    assert download.content == b"png-bytes"

    second = auth_client.post(
        f"/v1/goals/{goal_id}/icons",
        headers=headers,
        files={"file": ("icon2.png", io.BytesIO(b"new-png"), "image/png")},
    )
    assert second.status_code == 201
    second_id = second.json()["id"]
    assert second_id != icon_id
    assert len(storage._objects) == 2
    assert second.json()["goal"]["icon"] == second_id

    listed = auth_client.get(f"/v1/goals/{goal_id}/icons", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["max_per_goal"] == 3
    assert [item["id"] for item in listed_body["items"]] == [icon_id, second_id]

    select_first = auth_client.patch(
        f"/v1/goals/{goal_id}",
        headers=headers,
        json={"icon_type": "upload", "icon": icon_id},
    )
    assert select_first.status_code == 200
    assert select_first.json()["icon"] == icon_id

    delete = auth_client.delete(f"/v1/goals/icons/id/{icon_id}", headers=headers)
    assert delete.status_code == 204
    assert len(storage._objects) == 1

    goals = auth_client.get("/v1/goals", headers=headers)
    goal = next(item for item in goals.json()["items"] if item["id"] == goal_id)
    assert goal["icon_type"] == "upload"
    assert goal["icon"] == second_id

    delete_last = auth_client.delete(f"/v1/goals/icons/id/{second_id}", headers=headers)
    assert delete_last.status_code == 204
    assert len(storage._objects) == 0

    goals_after = auth_client.get("/v1/goals", headers=headers)
    goal_after = next(item for item in goals_after.json()["items"] if item["id"] == goal_id)
    assert goal_after["icon_type"] == "emoji"
    assert goal_after["icon"] == "🎯"


def test_goal_icon_upload_rejects_when_limit_reached(
    auth_client: TestClient,
    mailer: FakeEmailService,
    storage: FakeStorage,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"goal-icon-limit-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(token)
    goal_id = _first_goal_id(auth_client, headers)

    for index in range(3):
        response = auth_client.post(
            f"/v1/goals/{goal_id}/icons",
            headers=headers,
            files={"file": (f"icon{index}.png", io.BytesIO(f"png-{index}".encode()), "image/png")},
        )
        assert response.status_code == 201

    fourth = auth_client.post(
        f"/v1/goals/{goal_id}/icons",
        headers=headers,
        files={"file": ("extra.png", io.BytesIO(b"extra"), "image/png")},
    )
    assert fourth.status_code == 400
    assert len(storage._objects) == 3


def test_goal_style_patch_and_defaults(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"goal-style-{uuid.uuid4()}@example.com")
    headers = _auth_headers(token)

    listed = auth_client.get("/v1/goals", headers=headers)
    goal = listed.json()["items"][0]
    assert goal["color"] == "#60a5fa"
    assert goal["icon_type"] == "emoji"
    assert goal["icon"] == "🎯"

    patched = auth_client.patch(
        f"/v1/goals/{goal['id']}",
        headers=headers,
        json={"color": "#34d399", "icon_type": "emoji", "icon": "🏃"},
    )
    assert patched.status_code == 200
    assert patched.json()["color"] == "#34d399"
    assert patched.json()["icon"] == "🏃"

    created = auth_client.post(
        "/v1/goals",
        headers=headers,
        json={
            "labels": {"en": "Stretch"},
            "times_per_week": 3,
            "starts_on": "2026-07-01",
            "show_on_entry": False,
            "color": "#f59e0b",
            "icon_type": "emoji",
            "icon": "🧘",
        },
    )
    assert created.status_code == 201
    assert created.json()["color"] == "#f59e0b"
    assert created.json()["icon"] == "🧘"


def test_goal_calendar_groups_by_day_and_caps_marks(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(
        auth_client, mailer, f"goal-calendar-{uuid.uuid4()}@example.com"
    )
    headers = _auth_headers(token)

    goals = auth_client.get("/v1/goals", headers=headers).json()["items"]
    g1, g2, g3 = goals[0]["id"], goals[1]["id"], goals[2]["id"]

    for goal_id in (g1, g2, g3):
        patched = auth_client.patch(
            f"/v1/goals/{goal_id}",
            headers=headers,
            json={"starts_on": "2026-07-01"},
        )
        assert patched.status_code == 200

    # Newest entry first: two goals (incl. duplicate g2 later), then g2, then g3.
    # Same goal on multiple notes counts once per day.
    for payload in (
        {
            "score": 3,
            "recorded_at": "2026-07-14T10:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [g3],
        },
        {
            "score": 4,
            "recorded_at": "2026-07-14T14:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [g2],
        },
        {
            "score": 5,
            "recorded_at": "2026-07-14T18:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [g1, g2],
        },
        {
            "score": 4,
            "recorded_at": "2026-07-15T10:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [g1],
        },
        {
            "score": 2,
            "recorded_at": "2026-07-16T10:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [],
        },
    ):
        created = auth_client.post("/v1/mood-entries", headers=headers, json=payload)
        assert created.status_code == 201

    response = auth_client.get(
        "/v1/goals/calendar",
        params={
            "recorded_from": "2026-07-01T00:00:00+03:00",
            "recorded_to": "2026-08-01T00:00:00+03:00",
        },
        headers=headers,
    )
    assert response.status_code == 200
    days = {day["date"]: day for day in response.json()["days"]}
    assert set(days) == {"2026-07-14", "2026-07-15"}

    july_14 = days["2026-07-14"]
    assert july_14["entry_count"] == 3
    # Newest entry first (g1, g2), then older unique g3 — duplicate g2 dropped.
    assert [item["goal_id"] for item in july_14["goals"]] == [g1, g2, g3]

    july_15 = days["2026-07-15"]
    assert july_15["entry_count"] == 1
    assert july_15["goals"] == [{"goal_id": g1}]
