from datetime import date, timedelta

from app.models.goal import Goal
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user_goals(db: Session, email: str) -> list[Goal]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    goals = list(
        db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.sort_order)).all()
    )
    assert len(goals) >= 1
    return goals


def test_default_goals_provisioned_on_register(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "goals-default@example.com")
    headers = _auth_headers(token)

    response = auth_client.get("/v1/goals", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["entry_visible_goal_limit"] == 3
    items = body["items"]
    assert [item["slug"] for item in items] == ["early_rise", "min_screen_time", "exercise"]
    assert items[0]["times_per_week"] == 7
    assert items[0]["show_on_entry"] is True
    assert items[0]["completed_this_week"] == 0
    assert items[0]["label"] == "Early rise"


def test_goal_crud_and_visibility_limit(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "goals-crud@example.com")
    headers = _auth_headers(token)

    listed = auth_client.get("/v1/goals", headers=headers)
    assert listed.status_code == 200
    existing = listed.json()["items"]
    # Defaults already pin 3 visible goals — creating another visible one should fail.
    rejected = auth_client.post(
        "/v1/goals",
        json={
            "labels": {"en": "Extra goal"},
            "times_per_week": 4,
            "starts_on": "2026-07-01",
            "show_on_entry": True,
        },
        headers=headers,
    )
    assert rejected.status_code == 400

    created = auth_client.post(
        "/v1/goals",
        json={
            "labels": {"en": "Read books"},
            "times_per_week": 3,
            "starts_on": "2026-07-01",
            "show_on_entry": False,
        },
        headers=headers,
    )
    assert created.status_code == 201
    goal = created.json()
    assert goal["slug"] == "read_books"
    assert goal["times_per_week"] == 3
    goal_id = goal["id"]

    patched = auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"labels": {"en": "Read more"}, "times_per_week": 5},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["label"] == "Read more"
    assert patched.json()["times_per_week"] == 5

    # Unpin one default, then pin the custom goal.
    first_id = existing[0]["id"]
    unpin = auth_client.patch(
        f"/v1/goals/{first_id}",
        json={"show_on_entry": False},
        headers=headers,
    )
    assert unpin.status_code == 200

    pin = auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"show_on_entry": True},
        headers=headers,
    )
    assert pin.status_code == 200
    assert pin.json()["show_on_entry"] is True

    deleted = auth_client.delete(f"/v1/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204


def test_goal_week_stats_and_entry_linking(
    auth_client: TestClient,
    mailer,
    db: Session,
) -> None:
    email = "goals-week@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = _auth_headers(token)
    goals = _user_goals(db, email)
    goal = goals[0]
    goal_id = str(goal.id)

    # Entry before start date should reject the goal.
    future_start = (date.today() + timedelta(days=30)).isoformat()
    auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"starts_on": future_start},
        headers=headers,
    )
    rejected = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 4,
            "recorded_at": f"{date.today().isoformat()}T12:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [goal_id],
        },
        headers=headers,
    )
    assert rejected.status_code == 400

    # Pin start to the beginning of this ISO week and mark three distinct days.
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    completion_days = [week_start + timedelta(days=offset) for offset in (0, 1, 2)]
    auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"starts_on": week_start.isoformat(), "times_per_week": 7},
        headers=headers,
    )

    for day in completion_days:
        created = auth_client.post(
            "/v1/mood-entries",
            json={
                "score": 4,
                "recorded_at": f"{day.isoformat()}T09:00:00+03:00",
                "tag_ids": [],
                "goal_ids": [goal_id],
            },
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["goals"][0]["id"] == goal_id

    # Second entry same day should not double-count.
    duplicate_day = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 3,
            "recorded_at": f"{completion_days[2].isoformat()}T20:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [goal_id],
        },
        headers=headers,
    )
    assert duplicate_day.status_code == 201

    listed = auth_client.get("/v1/goals", headers=headers)
    assert listed.status_code == 200
    item = next(goal_item for goal_item in listed.json()["items"] if goal_item["id"] == goal_id)
    assert item["completed_this_week"] == 3
    assert item["times_per_week"] == 7


def test_goal_locale_and_reorder(
    auth_client: TestClient,
    mailer,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "goals-locale@example.com")
    headers = {**_auth_headers(token), "Accept-Language": "ru"}

    response = auth_client.get("/v1/goals", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    early = next(item for item in items if item["slug"] == "early_rise")
    assert early["label"] == "Ранний подъём"

    ordered_ids = [items[-1]["id"], *[item["id"] for item in items[:-1]]]
    reordered = auth_client.put(
        "/v1/goals/reorder",
        json={"ordered_ids": ordered_ids},
        headers=_auth_headers(token),
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()["items"]] == ordered_ids


def test_cannot_delete_linked_goal(
    auth_client: TestClient,
    mailer,
    db: Session,
) -> None:
    email = "goals-linked@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    headers = _auth_headers(token)
    goal_id = str(_user_goals(db, email)[0].id)

    auth_client.patch(
        f"/v1/goals/{goal_id}",
        json={"starts_on": "2026-07-01"},
        headers=headers,
    )
    created = auth_client.post(
        "/v1/mood-entries",
        json={
            "score": 4,
            "recorded_at": "2026-07-10T12:00:00+03:00",
            "tag_ids": [],
            "goal_ids": [goal_id],
        },
        headers=headers,
    )
    assert created.status_code == 201

    deleted = auth_client.delete(f"/v1/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 409
