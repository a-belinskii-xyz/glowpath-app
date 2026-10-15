"""Weight and food notes on «Моё» (GP-47)."""

import io
import json
import zipfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.body import FoodLog, Measurement
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _today(db: Session, email: str) -> date:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return datetime.now(ZoneInfo(user.timezone)).date()


def test_settings_start_off_and_can_link_only_own_goal(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, "body-settings@example.com")
    other = register_verify_and_login(auth_client, mailer, "body-settings-other@example.com")

    initial = auth_client.get("/v1/body/settings", headers=_auth(token))
    assert initial.status_code == 200
    assert initial.json() == {
        "show_weight": False,
        "show_food": False,
        "hide_weight": False,
        "food_goal_id": None,
    }

    goal = auth_client.post(
        "/v1/goals",
        json={"labels": {"en": "Eat properly"}, "times_per_week": 7, "starts_on": "2026-01-01"},
        headers=_auth(token),
    ).json()
    updated = auth_client.patch(
        "/v1/body/settings",
        json={"show_weight": True, "food_goal_id": goal["id"]},
        headers=_auth(token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["show_weight"] is True
    assert updated.json()["show_food"] is False
    assert updated.json()["food_goal_id"] == goal["id"]

    foreign = auth_client.patch(
        "/v1/body/settings", json={"food_goal_id": goal["id"]}, headers=_auth(other)
    )
    assert foreign.status_code == 404

    cleared = auth_client.patch(
        "/v1/body/settings", json={"food_goal_id": None}, headers=_auth(token)
    )
    assert cleared.json()["food_goal_id"] is None
    assert cleared.json()["show_weight"] is True

    # Deleting the linked goal just unlinks it.
    auth_client.patch("/v1/body/settings", json={"food_goal_id": goal["id"]}, headers=_auth(token))
    assert auth_client.delete(f"/v1/goals/{goal['id']}", headers=_auth(token)).status_code == 204
    assert auth_client.get("/v1/body/settings", headers=_auth(token)).json()["food_goal_id"] is None


def test_weight_is_one_per_day_and_rejects_future_days(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "body-weight@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    yesterday = today - timedelta(days=1)

    first = auth_client.put(
        f"/v1/body/weight/{yesterday}", json={"value": 82.4}, headers=_auth(token)
    )
    assert first.status_code == 200, first.text
    assert first.json() == {"day": yesterday.isoformat(), "value": 82.4}
    auth_client.put(f"/v1/body/weight/{today}", json={"value": 82.6}, headers=_auth(token))
    changed = auth_client.put(
        f"/v1/body/weight/{today}", json={"value": 82.1}, headers=_auth(token)
    )
    assert changed.json()["value"] == 82.1

    listed = auth_client.get(
        "/v1/body/weight",
        params={"from": (today - timedelta(days=30)).isoformat(), "to": today.isoformat()},
        headers=_auth(token),
    )
    assert listed.json()["items"] == [
        {"day": yesterday.isoformat(), "value": 82.4},
        {"day": today.isoformat(), "value": 82.1},
    ]

    future = auth_client.put(
        f"/v1/body/weight/{today + timedelta(days=3)}", json={"value": 80}, headers=_auth(token)
    )
    assert future.status_code == 400
    assert future.json()["detail"]["code"] == "body_day_in_future"
    too_precise = auth_client.put(
        f"/v1/body/weight/{today}", json={"value": 82.15}, headers=_auth(token)
    )
    assert too_precise.status_code == 422
    too_light = auth_client.put(f"/v1/body/weight/{today}", json={"value": 5}, headers=_auth(token))
    assert too_light.status_code == 422

    wide = auth_client.get(
        "/v1/body/weight",
        params={"from": "2020-01-01", "to": today.isoformat()},
        headers=_auth(token),
    )
    assert wide.status_code == 400
    assert wide.json()["detail"]["code"] == "invalid_body_range"

    assert auth_client.delete(f"/v1/body/weight/{today}", headers=_auth(token)).status_code == 204
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    days = list(db.scalars(select(Measurement.day).where(Measurement.user_id == user.id)))
    assert days == [yesterday]


def test_food_notes_can_be_added_edited_and_removed_by_owner_only(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "body-food@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    other = register_verify_and_login(auth_client, mailer, "body-food-other@example.com")
    today = _today(db, email)

    created = auth_client.post(
        "/v1/body/food",
        json={"day": today.isoformat(), "meal": "morning", "text": "  Oatmeal with banana  "},
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    note = created.json()
    assert note["text"] == "Oatmeal with banana"
    assert note["meal"] == "morning"
    auth_client.post(
        "/v1/body/food", json={"day": today.isoformat(), "text": "Soup"}, headers=_auth(token)
    )
    assert (
        auth_client.post(
            "/v1/body/food", json={"day": today.isoformat(), "text": "   "}, headers=_auth(token)
        ).status_code
        == 422
    )

    listed = auth_client.get(
        "/v1/body/food",
        params={"from": today.isoformat(), "to": today.isoformat()},
        headers=_auth(token),
    ).json()["items"]
    assert [item["text"] for item in listed] == ["Oatmeal with banana", "Soup"]
    assert listed[1]["meal"] is None

    patched = auth_client.patch(
        f"/v1/body/food/{note['id']}", json={"meal": None, "text": "Oats"}, headers=_auth(token)
    )
    assert patched.status_code == 200
    assert patched.json()["meal"] is None
    assert patched.json()["text"] == "Oats"

    assert (
        auth_client.delete(f"/v1/body/food/{note['id']}", headers=_auth(other)).status_code == 404
    )
    assert (
        auth_client.delete(f"/v1/body/food/{note['id']}", headers=_auth(token)).status_code == 204
    )
    assert (
        auth_client.get(
            "/v1/body/food",
            params={"from": today.isoformat(), "to": today.isoformat()},
            headers=_auth(other),
        ).json()["items"]
        == []
    )


def test_weight_and_food_survive_export_and_restore(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    source_email = "body-export@example.com"
    source = register_verify_and_login(auth_client, mailer, source_email)
    today = _today(db, source_email)
    auth_client.put(f"/v1/body/weight/{today}", json={"value": 82.4}, headers=_auth(source))
    auth_client.post(
        "/v1/body/food",
        json={"day": today.isoformat(), "meal": "day", "text": "Soup"},
        headers=_auth(source),
    )

    exported = auth_client.get("/v1/account/export", headers=_auth(source))
    payload = json.loads(zipfile.ZipFile(io.BytesIO(exported.content)).read("diary.json"))
    assert payload["weights"] == [{"day": today.isoformat(), "value_kg": 82.4}]
    assert payload["food"] == [{"day": today.isoformat(), "meal": "day", "text": "Soup"}]

    target_email = "body-import@example.com"
    target = register_verify_and_login(auth_client, mailer, target_email)
    for _ in range(2):
        preview = auth_client.post(
            "/v1/account/restores",
            headers=_auth(target),
            files=[("files", ("part1.zip", exported.content, "application/zip"))],
        )
        assert preview.status_code == 201, preview.text
        applied = auth_client.post(
            f"/v1/account/restores/{preview.json()['id']}/apply", headers=_auth(target)
        )
        assert applied.status_code == 200, applied.text

    target_user = db.scalar(select(User).where(User.email == target_email))
    assert target_user is not None
    weights = list(db.scalars(select(Measurement).where(Measurement.user_id == target_user.id)))
    assert [(item.day, float(item.value)) for item in weights] == [(today, 82.4)]
    food = list(db.scalars(select(FoodLog).where(FoodLog.user_id == target_user.id)))
    assert [(item.day, item.meal, item.text) for item in food] == [(today, "day", "Soup")]
