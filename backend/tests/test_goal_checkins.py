"""Marking a goal done without a mood entry, "a little" or fully (GP-43)."""

import io
import json
import zipfile
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.models.goal import Goal
from app.models.goal_checkin import GoalCheckin
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


def _create_goal(client: TestClient, token: str, **extra: Any) -> dict[str, Any]:
    response = client.post(
        "/v1/goals",
        json={"labels": {"en": "Eat properly"}, "times_per_week": 7, "starts_on": "2026-01-01"}
        | extra,
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _check_in(
    client: TestClient, token: str, goal_id: str, day: date, level: str = "partial"
) -> Any:
    return client.put(
        f"/v1/goals/{goal_id}/checkins/{day.isoformat()}",
        json={"level": level},
        headers=_auth(token),
    )


def _listed(client: TestClient, token: str, goal_id: str, on: date) -> dict[str, Any]:
    response = client.get("/v1/goals", params={"progress_on": on.isoformat()}, headers=_auth(token))
    assert response.status_code == 200
    return next(item for item in response.json()["items"] if item["id"] == goal_id)


def test_check_in_counts_and_can_be_changed_or_removed(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "checkin-basic@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    goal = _create_goal(auth_client, token, partial_label="at least a snack")
    assert goal["partial_label"] == "at least a snack"
    assert goal["week_marks"] == []

    marked = _check_in(auth_client, token, goal["id"], today)
    assert marked.status_code == 200, marked.text
    assert marked.json()["completed_this_week"] == 1
    assert marked.json()["week_marks"] == [
        {"date": today.isoformat(), "level": "partial", "amount": None}
    ]
    # Amounts belong to entries only.
    assert marked.json()["day_amount"] == 0

    full = _check_in(auth_client, token, goal["id"], today, "full")
    assert full.json()["week_marks"] == [
        {"date": today.isoformat(), "level": "full", "amount": None}
    ]
    listed = _listed(auth_client, token, goal["id"], today)
    assert listed["completed_this_week"] == 1
    assert listed["week_marks"] == [{"date": today.isoformat(), "level": "full", "amount": None}]

    removed = auth_client.delete(
        f"/v1/goals/{goal['id']}/checkins/{today.isoformat()}", headers=_auth(token)
    )
    assert removed.status_code == 200
    assert removed.json()["completed_this_week"] == 0
    assert removed.json()["week_marks"] == []
    # Removing a day that has no check-in is a no-op.
    again = auth_client.delete(
        f"/v1/goals/{goal['id']}/checkins/{today.isoformat()}", headers=_auth(token)
    )
    assert again.status_code == 200


def test_check_in_respects_goal_dates_and_rejects_the_future(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "checkin-dates@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    goal = _create_goal(
        auth_client,
        token,
        starts_on=(today - timedelta(days=2)).isoformat(),
        ends_on=today.isoformat(),
    )

    future = _check_in(auth_client, token, goal["id"], today + timedelta(days=3))
    assert future.status_code == 400
    assert future.json()["detail"]["code"] == "goal_checkin_in_future"

    early = _check_in(auth_client, token, goal["id"], today - timedelta(days=5))
    assert early.status_code == 400
    assert early.json()["detail"]["code"] == "goal_not_available_before"

    bad_level = auth_client.put(
        f"/v1/goals/{goal['id']}/checkins/{today.isoformat()}",
        json={"level": "half"},
        headers=_auth(token),
    )
    assert bad_level.status_code == 422


def test_check_in_is_private_to_the_goal_owner(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    owner = register_verify_and_login(auth_client, mailer, "checkin-owner@example.com")
    goal = _create_goal(auth_client, owner)
    other = register_verify_and_login(auth_client, mailer, "checkin-other@example.com")
    today = _today(db, "checkin-other@example.com")

    assert _check_in(auth_client, other, goal["id"], today).status_code == 404
    deleted = auth_client.delete(
        f"/v1/goals/{goal['id']}/checkins/{today.isoformat()}", headers=_auth(other)
    )
    assert deleted.status_code == 404


def test_entry_day_shows_as_full_and_check_ins_feed_stats_and_calendar(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "checkin-stats@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    week_start = today - timedelta(days=today.weekday())
    goal = _create_goal(auth_client, token, show_in_stats=True)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    offset = datetime.now(ZoneInfo(user.timezone)).strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}"

    # Week start: an entry plus a "partial" check-in; the entry wins.
    entry = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 4,
            "recorded_at": f"{week_start.isoformat()}T12:00:00{offset}",
            "tag_ids": [],
            "goal_ids": [goal["id"]],
        },
        headers=_auth(token),
    )
    assert entry.status_code == 201, entry.text
    assert _check_in(auth_client, token, goal["id"], week_start).status_code == 200
    second_day = week_start + timedelta(days=1)
    if second_day <= today:
        assert _check_in(auth_client, token, goal["id"], second_day).status_code == 200

    listed = _listed(auth_client, token, goal["id"], week_start)
    expected = [{"date": week_start.isoformat(), "level": "full", "amount": None}]
    if second_day <= today:
        expected.append({"date": second_day.isoformat(), "level": "partial", "amount": None})
    assert listed["week_marks"] == expected
    assert listed["completed_this_week"] == len(expected)

    params = {
        "recorded_from": f"{week_start.isoformat()}T00:00:00{offset}",
        "recorded_to": f"{(week_start + timedelta(days=7)).isoformat()}T00:00:00{offset}",
    }
    stats = auth_client.get("/v1/goals/stats", params=params, headers=_auth(token))
    assert stats.status_code == 200
    item = next(item for item in stats.json()["items"] if item["id"] == goal["id"])
    assert item["completed_in_period"] == len(expected)

    calendar = auth_client.get("/v1/goals/calendar", params=params, headers=_auth(token))
    assert calendar.status_code == 200
    marked_days = {
        day["date"]
        for day in calendar.json()["days"]
        if any(mark["goal_id"] == goal["id"] for mark in day["goals"])
    }
    assert marked_days == {mark["date"] for mark in expected}
    first = next(day for day in calendar.json()["days"] if day["date"] == week_start.isoformat())
    # The same goal from an entry and a check-in counts once.
    assert [mark["goal_id"] for mark in first["goals"]].count(goal["id"]) == 1


def test_partial_label_patch_clear_and_limit(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, "checkin-label@example.com")
    goal = _create_goal(auth_client, token)
    assert goal["partial_label"] is None

    patched = auth_client.patch(
        f"/v1/goals/{goal['id']}",
        json={"partial_label": "  go outside for 5 minutes  "},
        headers=_auth(token),
    )
    assert patched.status_code == 200
    assert patched.json()["partial_label"] == "go outside for 5 minutes"

    untouched = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"times_per_week": 3}, headers=_auth(token)
    )
    assert untouched.json()["partial_label"] == "go outside for 5 minutes"

    cleared = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"partial_label": ""}, headers=_auth(token)
    )
    assert cleared.json()["partial_label"] is None

    too_long = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"partial_label": "x" * 81}, headers=_auth(token)
    )
    assert too_long.status_code == 422


def test_deleting_a_goal_removes_its_check_ins(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    email = "checkin-delete@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    goal = _create_goal(auth_client, token)
    assert _check_in(auth_client, token, goal["id"], _today(db, email)).status_code == 200

    deleted = auth_client.delete(f"/v1/goals/{goal['id']}", headers=_auth(token))
    assert deleted.status_code == 204
    db.expire_all()
    assert db.scalar(select(GoalCheckin).where(GoalCheckin.goal_id == goal["id"])) is None


def test_check_ins_survive_export_and_restore(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    source_email = "checkin-export@example.com"
    source = register_verify_and_login(auth_client, mailer, source_email)
    today = _today(db, source_email)
    goal = _create_goal(auth_client, source, partial_label="a snack")
    assert _check_in(auth_client, source, goal["id"], today).status_code == 200
    yesterday = today - timedelta(days=1)
    assert _check_in(auth_client, source, goal["id"], yesterday, "full").status_code == 200

    exported = auth_client.get("/v1/account/export", headers=_auth(source))
    assert exported.status_code == 200
    payload = json.loads(zipfile.ZipFile(io.BytesIO(exported.content)).read("diary.json"))
    archived = next(item for item in payload["goals"] if item["slug"] == goal["slug"])
    assert archived["partial_label"] == "a snack"
    assert archived["checkins"] == [
        {"day": yesterday.isoformat(), "level": "full", "amount": None},
        {"day": today.isoformat(), "level": "partial", "amount": None},
    ]

    target_email = "checkin-import@example.com"
    target = register_verify_and_login(auth_client, mailer, target_email)
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
    restored = db.scalar(
        select(Goal).where(Goal.user_id == target_user.id, Goal.slug == goal["slug"])
    )
    assert restored is not None
    assert restored.partial_label == "a snack"
    marks = {
        (checkin.day, checkin.level)
        for checkin in db.scalars(select(GoalCheckin).where(GoalCheckin.goal_id == restored.id))
    }
    assert marks == {(yesterday, "full"), (today, "partial")}

    # A second restore of the same archive adds nothing.
    again = auth_client.post(
        "/v1/account/restores",
        headers=_auth(target),
        files=[("files", ("part1.zip", exported.content, "application/zip"))],
    )
    auth_client.post(f"/v1/account/restores/{again.json()['id']}/apply", headers=_auth(target))
    count = len(list(db.scalars(select(GoalCheckin).where(GoalCheckin.goal_id == restored.id))))
    assert count == 2


def test_quantity_check_in_counts_from_the_minimum(
    auth_client: TestClient, mailer: FakeEmailService, db: Session
) -> None:
    """GP-46: a quantity day counts from ``min_amount``; less shows as started."""
    email = "checkin-quantity@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    today = _today(db, email)
    goal = _create_goal(
        auth_client,
        token,
        tracking_kind="quantity",
        target_amount=100,
        unit="pages",
        min_amount=60,
    )
    assert goal["min_amount"] == 60

    needs_amount = _check_in(auth_client, token, goal["id"], today)
    assert needs_amount.status_code == 422
    assert needs_amount.json()["detail"]["code"] == "goal_checkin_amount_required"

    def put(amount: int) -> dict[str, Any]:
        response = auth_client.put(
            f"/v1/goals/{goal['id']}/checkins/{today.isoformat()}",
            json={"amount": amount},
            headers=_auth(token),
        )
        assert response.status_code == 200, response.text
        return response.json()

    below = put(40)
    assert below["week_marks"] == [{"date": today.isoformat(), "level": "started", "amount": 40}]
    assert below["completed_this_week"] == 0
    assert below["day_amount"] == 40

    counted = put(78)
    assert counted["week_marks"] == [{"date": today.isoformat(), "level": "partial", "amount": 78}]
    assert counted["completed_this_week"] == 1

    full = put(100)
    assert full["week_marks"][0]["level"] == "full"

    # Without a minimum only the full target counts.
    cleared = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"min_amount": None}, headers=_auth(token)
    )
    assert cleared.json()["min_amount"] is None
    assert put(78)["completed_this_week"] == 0

    too_big = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"min_amount": 150}, headers=_auth(token)
    )
    assert too_big.status_code == 400
    assert too_big.json()["detail"]["code"] == "invalid_goal_min_amount"

    # Lowering the target keeps the minimum inside it.
    auth_client.patch(f"/v1/goals/{goal['id']}", json={"min_amount": 60}, headers=_auth(token))
    lowered = auth_client.patch(
        f"/v1/goals/{goal['id']}", json={"target_amount": 50}, headers=_auth(token)
    )
    assert lowered.json()["min_amount"] == 50
