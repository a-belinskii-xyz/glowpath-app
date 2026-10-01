import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.core.security import create_access_token
from app.models.mood_entry import MoodEntry
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.notifications import (
    EmailNotifier,
    NotificationChannel,
    NotificationDispatcher,
    process_due_reminders,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

START = datetime(2026, 10, 5, 21, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _enable_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", True)
    monkeypatch.setattr(settings, "notifications_match_window_minutes", 30)


def _user_with_daily_email(db: Session) -> tuple[User, UserNotificationSchedule]:
    user = User(
        email=f"backoff-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone="UTC",
        email_verified_at=START - timedelta(days=30),
    )
    db.add(user)
    db.flush()
    schedule = UserNotificationSchedule(
        user_id=user.id,
        kind="daily_mood",
        enabled=True,
        time_of_day="21:00",
        interval_days=1,
        channels=["email"],
    )
    db.add(schedule)
    db.commit()
    return user, schedule


def _run_days(
    db: Session,
    mailer: FakeEmailService,
    days: range,
) -> list[int]:
    """Tick once a day at reminder time; return the days an email went out."""
    dispatcher = NotificationDispatcher({NotificationChannel.EMAIL: EmailNotifier(mailer)})
    sent_days: list[int] = []
    for day in days:
        before = len(mailer.outbox)
        process_due_reminders(db, dispatcher, now=START + timedelta(days=day))
        if len(mailer.outbox) > before:
            sent_days.append(day)
    return sent_days


def _add_entry(db: Session, user: User, at: datetime) -> None:
    db.add(
        MoodEntry(
            user_id=user.id,
            recorded_at=at,
            created_at=at,
            score=4,
            score_color="#00aa00",
        )
    )
    db.commit()


def test_ignored_reminders_slow_down_then_pause(db: Session, mailer: FakeEmailService) -> None:
    _, schedule = _user_with_daily_email(db)

    sent_days = _run_days(db, mailer, range(0, 40))

    # Daily twice, then every 2, 4, 4, 7, 7 days; the last email says reminders are paused.
    assert sent_days == [0, 1, 3, 7, 11, 18, 25, 32]
    assert "паузу" in mailer.outbox[-1].subject or "Pausing" in mailer.outbox[-1].subject
    db.refresh(schedule)
    assert schedule.paused_at == START + timedelta(days=32)
    assert schedule.enabled is True


def test_entry_after_reminder_resets_the_streak(db: Session, mailer: FakeEmailService) -> None:
    user, _ = _user_with_daily_email(db)
    assert _run_days(db, mailer, range(0, 4)) == [0, 1, 3]

    _add_entry(db, user, START + timedelta(days=3, hours=1))

    # Back to daily reminders after the person wrote an entry.
    assert _run_days(db, mailer, range(4, 7)) == [4, 5]


def test_followed_link_resets_the_streak(
    auth_client: TestClient,
    db: Session,
    mailer: FakeEmailService,
) -> None:
    _, schedule = _user_with_daily_email(db)
    assert _run_days(db, mailer, range(0, 4)) == [0, 1, 3]
    latest = db.scalar(
        select(NotificationDelivery)
        .where(NotificationDelivery.schedule_id == schedule.id)
        .order_by(NotificationDelivery.sent_at.desc())
        .limit(1)
    )
    assert latest is not None
    assert f"n={latest.token}" in mailer.outbox[-1].body

    response = auth_client.post("/v1/notification-settings/engaged", params={"token": latest.token})

    assert response.status_code == 204
    assert _run_days(db, mailer, range(4, 6)) == [4, 5]


def test_unknown_engagement_token_is_ignored(auth_client: TestClient) -> None:
    response = auth_client.post("/v1/notification-settings/engaged", params={"token": "nope"})
    assert response.status_code == 204


def test_paused_schedule_shows_off_and_resumes_from_settings(
    auth_client: TestClient,
    db: Session,
    mailer: FakeEmailService,
) -> None:
    user, schedule = _user_with_daily_email(db)
    _run_days(db, mailer, range(0, 33))
    db.refresh(schedule)
    assert schedule.paused_at is not None
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}

    listed = auth_client.get("/v1/notification-settings", headers=headers).json()
    daily = next(item for item in listed["schedules"] if item["kind"] == "daily_mood")
    assert daily["enabled"] is False
    assert daily["paused_at"] is not None

    patched = auth_client.patch(
        "/v1/notification-settings/daily_mood", headers=headers, json={"enabled": True}
    )
    assert patched.status_code == 200
    daily = next(item for item in patched.json()["schedules"] if item["kind"] == "daily_mood")
    assert daily["enabled"] is True
    assert daily["paused_at"] is None
    db.refresh(schedule)
    assert schedule.paused_at is None
    assert schedule.backoff_reset_at is not None


@pytest.mark.parametrize("opt_in", [True, False])
def test_onboarding_email_reminder_opt_in(
    auth_client: TestClient,
    db: Session,
    mailer: FakeEmailService,
    opt_in: bool,
) -> None:
    email = f"onboard-remind-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)

    response = auth_client.post(
        "/v1/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"skip": True, "email_reminders": opt_in},
    )

    assert response.status_code == 200
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    daily = db.scalar(
        select(UserNotificationSchedule).where(
            UserNotificationSchedule.user_id == user.id,
            UserNotificationSchedule.kind == "daily_mood",
        )
    )
    assert daily is not None
    assert daily.enabled is opt_in
    assert daily.channels == ["email"]


def test_resumed_schedule_starts_a_fresh_count(db: Session, mailer: FakeEmailService) -> None:
    _, schedule = _user_with_daily_email(db)
    _run_days(db, mailer, range(0, 33))
    db.refresh(schedule)
    schedule.paused_at = None
    schedule.backoff_reset_at = START + timedelta(days=33)
    db.commit()

    assert _run_days(db, mailer, range(34, 37)) == [34, 35]
