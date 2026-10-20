"""Weight, food, sleep and workouts on «Моё» (GP-47, GP-48, GP-58)."""

import io
import json
import zipfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.body import Exercise, FoodLog, Measurement, SleepLog, WorkoutSet
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


def test_settings_start_off_and_link_up_to_three_own_goals(
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
        "show_sleep": False,
        "height_cm": None,
        "show_workouts": False,
        "food_goal_ids": [],
    }

    goals = [
        auth_client.post(
            "/v1/goals",
            json={
                "labels": {"en": f"Goal {index}"},
                "times_per_week": 7,
                "starts_on": "2026-01-01",
            },
            headers=_auth(token),
        ).json()["id"]
        for index in range(4)
    ]
    updated = auth_client.patch(
        "/v1/body/settings",
        json={"show_weight": True, "food_goal_ids": goals[:3]},
        headers=_auth(token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["show_weight"] is True
    assert updated.json()["show_food"] is False
    assert updated.json()["food_goal_ids"] == goals[:3]
    reordered = auth_client.patch(
        "/v1/body/settings", json={"food_goal_ids": [goals[2], goals[0]]}, headers=_auth(token)
    )
    assert reordered.json()["food_goal_ids"] == [goals[2], goals[0]]
    auth_client.patch("/v1/body/settings", json={"food_goal_ids": goals[:3]}, headers=_auth(token))

    too_many = auth_client.patch(
        "/v1/body/settings", json={"food_goal_ids": goals}, headers=_auth(token)
    )
    assert too_many.status_code == 422
    foreign = auth_client.patch(
        "/v1/body/settings", json={"food_goal_ids": [goals[0]]}, headers=_auth(other)
    )
    assert foreign.status_code == 404

    # Other fields leave the goals alone; deleting a linked goal just unlinks it.
    kept = auth_client.patch("/v1/body/settings", json={"show_food": True}, headers=_auth(token))
    assert kept.json()["food_goal_ids"] == goals[:3]
    assert auth_client.delete(f"/v1/goals/{goals[1]}", headers=_auth(token)).status_code == 204
    after = auth_client.get("/v1/body/settings", headers=_auth(token)).json()
    assert after["food_goal_ids"] == [goals[0], goals[2]]

    cleared = auth_client.patch(
        "/v1/body/settings", json={"food_goal_ids": []}, headers=_auth(token)
    )
    assert cleared.json()["food_goal_ids"] == []


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
    auth_client.put(
        f"/v1/body/sleep/{today}",
        json={"bed_time": "23:40", "wake_time": "07:10", "quality": "ok"},
        headers=_auth(source),
    )

    exported = auth_client.get("/v1/account/export", headers=_auth(source))
    payload = json.loads(zipfile.ZipFile(io.BytesIO(exported.content)).read("diary.json"))
    assert payload["weights"] == [{"day": today.isoformat(), "value_kg": 82.4}]
    assert payload["food"] == [{"day": today.isoformat(), "meal": "day", "text": "Soup"}]
    assert payload["sleep"] == [
        {
            "day": today.isoformat(),
            "bed_time": "23:40:00",
            "wake_time": "07:10:00",
            "up_time": None,
            "quality": "ok",
            "note": None,
        }
    ]

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
    nights = list(db.scalars(select(SleepLog).where(SleepLog.user_id == target_user.id)))
    assert [(item.day, item.bed_time.isoformat(), item.quality) for item in nights] == [
        (today, "23:40:00", "ok")
    ]


def test_sleep_is_one_night_per_day_and_height_can_be_forgotten(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "body-sleep@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    yesterday = today - timedelta(days=1)

    first = auth_client.put(
        f"/v1/body/sleep/{yesterday}",
        json={"bed_time": "00:30:45", "wake_time": "08:00", "up_time": "08:20", "note": "  "},
        headers=_auth(token),
    )
    assert first.status_code == 200, first.text
    assert first.json() == {
        "day": yesterday.isoformat(),
        "bed_time": "00:30:00",
        "wake_time": "08:00:00",
        "up_time": "08:20:00",
        "quality": None,
        "note": None,
    }
    auth_client.put(
        f"/v1/body/sleep/{today}",
        json={"bed_time": "23:00", "wake_time": "06:30", "quality": "good", "note": "Rain"},
        headers=_auth(token),
    )
    changed = auth_client.put(
        f"/v1/body/sleep/{today}",
        json={"bed_time": "23:15", "wake_time": "06:45", "quality": "hard"},
        headers=_auth(token),
    )
    assert changed.json()["quality"] == "hard"
    assert changed.json()["note"] is None

    listed = auth_client.get(
        "/v1/body/sleep",
        params={"from": (today - timedelta(days=7)).isoformat(), "to": today.isoformat()},
        headers=_auth(token),
    ).json()["items"]
    assert [(item["day"], item["bed_time"]) for item in listed] == [
        (yesterday.isoformat(), "00:30:00"),
        (today.isoformat(), "23:15:00"),
    ]

    future = auth_client.put(
        f"/v1/body/sleep/{today + timedelta(days=3)}",
        json={"bed_time": "23:00", "wake_time": "07:00"},
        headers=_auth(token),
    )
    assert future.status_code == 400
    assert future.json()["detail"]["code"] == "body_day_in_future"
    bad_quality = auth_client.put(
        f"/v1/body/sleep/{today}",
        json={"bed_time": "23:00", "wake_time": "07:00", "quality": "awful"},
        headers=_auth(token),
    )
    assert bad_quality.status_code == 422

    assert auth_client.delete(f"/v1/body/sleep/{today}", headers=_auth(token)).status_code == 204
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    days = list(db.scalars(select(SleepLog.day).where(SleepLog.user_id == user.id)))
    assert days == [yesterday]

    height = auth_client.patch(
        "/v1/body/settings", json={"show_sleep": True, "height_cm": 178.5}, headers=_auth(token)
    )
    assert height.json()["show_sleep"] is True
    assert height.json()["height_cm"] == 178.5
    kept = auth_client.patch("/v1/body/settings", json={"show_food": True}, headers=_auth(token))
    assert kept.json()["height_cm"] == 178.5
    too_tall = auth_client.patch("/v1/body/settings", json={"height_cm": 300}, headers=_auth(token))
    assert too_tall.status_code == 422
    forgotten = auth_client.patch(
        "/v1/body/settings", json={"height_cm": None}, headers=_auth(token)
    )
    assert forgotten.json()["height_cm"] is None


def test_workouts_replace_sets_per_exercise_and_day(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "body-workouts@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    other = register_verify_and_login(auth_client, mailer, "body-workouts-other@example.com")
    today = _today(db, email)
    yesterday = today - timedelta(days=1)

    shown = auth_client.patch(
        "/v1/body/settings", json={"show_workouts": True}, headers=_auth(token)
    )
    assert shown.json()["show_workouts"] is True

    bench = auth_client.post(
        "/v1/body/exercises", json={"name": "  Жим   лёжа "}, headers=_auth(token)
    )
    assert bench.status_code == 201
    assert bench.json()["name"] == "Жим лёжа"
    assert bench.json()["with_weight"] is True
    bench_id = bench.json()["id"]
    same = auth_client.post("/v1/body/exercises", json={"name": "жим лёжа"}, headers=_auth(token))
    assert same.json()["id"] == bench_id
    pullups = auth_client.post(
        "/v1/body/exercises",
        json={"name": "Подтягивания", "with_weight": False},
        headers=_auth(token),
    ).json()

    saved = auth_client.put(
        f"/v1/body/workouts/{yesterday}/{bench_id}",
        json={"sets": [{"weight_kg": 60, "reps": 8}, {"weight_kg": 62.5, "reps": 6}]},
        headers=_auth(token),
    )
    assert saved.status_code == 200, saved.text
    assert [
        (item["position"], item["weight_kg"], item["reps"]) for item in saved.json()["items"]
    ] == [
        (0, 60.0, 8),
        (1, 62.5, 6),
    ]
    replaced = auth_client.put(
        f"/v1/body/workouts/{yesterday}/{bench_id}",
        json={"sets": [{"weight_kg": 65, "reps": 5}]},
        headers=_auth(token),
    )
    assert [item["reps"] for item in replaced.json()["items"]] == [5]
    # Bodyweight exercises drop any weight sent.
    bodyweight = auth_client.put(
        f"/v1/body/workouts/{today}/{pullups['id']}",
        json={"sets": [{"weight_kg": 10, "reps": 7}, {"reps": 6}]},
        headers=_auth(token),
    )
    assert [item["weight_kg"] for item in bodyweight.json()["items"]] == [None, None]

    listed = auth_client.get(
        "/v1/body/workouts",
        params={"from": yesterday.isoformat(), "to": today.isoformat()},
        headers=_auth(token),
    ).json()["items"]
    assert [(item["day"], item["reps"]) for item in listed] == [
        (yesterday.isoformat(), 5),
        (today.isoformat(), 7),
        (today.isoformat(), 6),
    ]
    only_bench = auth_client.get(
        "/v1/body/workouts",
        params={"from": yesterday.isoformat(), "to": today.isoformat(), "exercise_id": bench_id},
        headers=_auth(token),
    ).json()["items"]
    assert len(only_bench) == 1

    exercises = auth_client.get("/v1/body/exercises", headers=_auth(token)).json()["items"]
    assert [(item["name"], item["last_day"], item["recent_days"]) for item in exercises] == [
        ("Подтягивания", today.isoformat(), 1),
        ("Жим лёжа", yesterday.isoformat(), 1),
    ]

    future = auth_client.put(
        f"/v1/body/workouts/{today + timedelta(days=3)}/{bench_id}",
        json={"sets": [{"weight_kg": 60, "reps": 8}]},
        headers=_auth(token),
    )
    assert future.status_code == 400
    zero = auth_client.put(
        f"/v1/body/workouts/{today}/{bench_id}",
        json={"sets": [{"weight_kg": 60, "reps": 0}]},
        headers=_auth(token),
    )
    assert zero.status_code == 422
    stranger = auth_client.put(
        f"/v1/body/workouts/{today}/{bench_id}",
        json={"sets": [{"weight_kg": 60, "reps": 8}]},
        headers=_auth(other),
    )
    assert stranger.status_code == 404
    assert auth_client.get("/v1/body/exercises", headers=_auth(other)).json()["items"] == []

    cleared = auth_client.put(
        f"/v1/body/workouts/{yesterday}/{bench_id}", json={"sets": []}, headers=_auth(token)
    )
    assert cleared.json()["items"] == []

    taken = auth_client.patch(
        f"/v1/body/exercises/{bench_id}", json={"name": "подтягивания"}, headers=_auth(token)
    )
    assert taken.status_code == 409
    renamed = auth_client.patch(
        f"/v1/body/exercises/{bench_id}",
        json={"name": "Жим лёжа узким", "with_weight": True},
        headers=_auth(token),
    )
    assert renamed.json()["name"] == "Жим лёжа узким"

    removed = auth_client.delete(f"/v1/body/exercises/{pullups['id']}", headers=_auth(token))
    assert removed.status_code == 204
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    assert db.scalars(select(WorkoutSet).where(WorkoutSet.user_id == user.id)).all() == []


def test_workouts_survive_export_and_restore(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    source_email = "body-workouts-export@example.com"
    source = register_verify_and_login(auth_client, mailer, source_email)
    today = _today(db, source_email)
    squat = auth_client.post(
        "/v1/body/exercises", json={"name": "Присед"}, headers=_auth(source)
    ).json()
    auth_client.put(
        f"/v1/body/workouts/{today}/{squat['id']}",
        json={"sets": [{"weight_kg": 80, "reps": 5}, {"weight_kg": 80, "reps": 4}]},
        headers=_auth(source),
    )

    exported = auth_client.get("/v1/account/export", headers=_auth(source))
    payload = json.loads(zipfile.ZipFile(io.BytesIO(exported.content)).read("diary.json"))
    assert payload["exercises"] == [
        {
            "name": "Присед",
            "with_weight": True,
            "sets": [
                {"day": today.isoformat(), "weight_kg": 80.0, "reps": 5},
                {"day": today.isoformat(), "weight_kg": 80.0, "reps": 4},
            ],
        }
    ]

    target_email = "body-workouts-import@example.com"
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
    exercises = list(db.scalars(select(Exercise).where(Exercise.user_id == target_user.id)))
    assert [item.name for item in exercises] == ["Присед"]
    sets = list(
        db.scalars(
            select(WorkoutSet)
            .where(WorkoutSet.user_id == target_user.id)
            .order_by(WorkoutSet.position)
        )
    )
    assert [(item.day, item.position, float(item.weight_kg or 0), item.reps) for item in sets] == [
        (today, 0, 80.0, 5),
        (today, 1, 80.0, 4),
    ]
