import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.api.v1.internal import get_notification_dispatcher
from app.config import Settings, settings
from app.main import app
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.notifications import (
    EmailNotifier,
    FakeNotifier,
    NotificationChannel,
    NotificationDispatcher,
    process_due_reminders,
)
from app.services.notifications.reminders import claim_schedule, release_schedule_claim
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService

CRON_SECRET = "test-cron-secret"
TICK_URL = "/v1/internal/reminders/tick"


@pytest.fixture(autouse=True)
def _enable_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", True)
    monkeypatch.setattr(settings, "notifications_worker_enabled", True)
    monkeypatch.setattr(settings, "notifications_match_window_minutes", 30)
    monkeypatch.setattr(settings, "reminders_cron_secret", CRON_SECRET)


def _add_daily_schedule(
    db: Session,
    *,
    tz_name: str,
    time_of_day: str,
    channels: list[str] | None = None,
) -> tuple[User, UserNotificationSchedule]:
    user = User(
        email=f"tick-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    schedule = UserNotificationSchedule(
        user_id=user.id,
        kind="daily_mood",
        enabled=True,
        time_of_day=time_of_day,
        interval_days=1,
        channels=channels if channels is not None else ["email"],
    )
    db.add(schedule)
    db.commit()
    return user, schedule


def _email_dispatcher(mailer: FakeEmailService) -> NotificationDispatcher:
    return NotificationDispatcher({NotificationChannel.EMAIL: EmailNotifier(mailer)})


def test_default_match_window_allows_catch_up() -> None:
    assert Settings.model_fields["notifications_match_window_minutes"].default == 30


def test_tick_is_not_found_without_configured_secret(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "reminders_cron_secret", "")
    response = auth_client.post(TICK_URL, headers={"Authorization": "Bearer anything"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": CRON_SECRET},
        {"Authorization": f"Basic {CRON_SECRET}"},
    ],
)
def test_tick_rejects_bad_secret(auth_client: TestClient, headers: dict[str, str]) -> None:
    response = auth_client.post(TICK_URL, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_cron_secret"


def test_tick_reports_disabled_feature(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", False)
    response = auth_client.post(TICK_URL, headers={"Authorization": f"Bearer {CRON_SECRET}"})
    assert response.status_code == 200
    assert response.json()["outcome"] == "feature_disabled"


def test_tick_sends_due_reminder_once(
    auth_client: TestClient,
    db: Session,
    mailer: FakeEmailService,
) -> None:
    now = datetime.now(UTC)
    _add_daily_schedule(db, tz_name="UTC", time_of_day=now.strftime("%H:%M"))
    app.dependency_overrides[get_notification_dispatcher] = lambda: _email_dispatcher(mailer)
    headers = {"Authorization": f"Bearer {CRON_SECRET}"}

    first = auth_client.post(TICK_URL, headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["outcome"] == "done"
    assert body["daily_mood_sent"] == 1
    assert body["errors"] == 0
    assert len(mailer.outbox) == 1

    second = auth_client.post(TICK_URL, headers=headers)
    assert second.status_code == 200
    assert second.json()["daily_mood_sent"] == 0
    assert len(mailer.outbox) == 1


@pytest.mark.parametrize(("minutes_late", "expected_sent"), [(0, 1), (20, 1), (29, 1), (31, 0)])
def test_missed_tick_catches_up_within_window(
    db: Session,
    minutes_late: int,
    expected_sent: int,
) -> None:
    tz_name = "Europe/Minsk"
    _add_daily_schedule(db, tz_name=tz_name, time_of_day="20:30")
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=ZoneInfo(tz_name)) + timedelta(
        minutes=minutes_late
    )
    mailer = FakeEmailService()

    stats = process_due_reminders(db, _email_dispatcher(mailer), now=local_now.astimezone(UTC))

    assert stats.daily_mood_sent == expected_sent
    assert len(mailer.outbox) == expected_sent


def test_reminder_is_not_sent_before_its_time(db: Session) -> None:
    tz_name = "Europe/Minsk"
    _add_daily_schedule(db, tz_name=tz_name, time_of_day="20:30")
    local_now = datetime(2026, 7, 15, 20, 29, 50, tzinfo=ZoneInfo(tz_name))
    mailer = FakeEmailService()

    stats = process_due_reminders(db, _email_dispatcher(mailer), now=local_now.astimezone(UTC))

    assert stats.daily_mood_sent == 0
    assert mailer.outbox == []


def test_claim_schedule_lets_only_one_run_win(db: Session) -> None:
    _, schedule = _add_daily_schedule(db, tz_name="UTC", time_of_day="08:00")
    at = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)

    assert claim_schedule(db, schedule_id=schedule.id, previous=None, at=at) is True
    # An overlapping run loaded the schedule before the claim and still sees None.
    assert claim_schedule(db, schedule_id=schedule.id, previous=None, at=at) is False

    release_schedule_claim(db, schedule_id=schedule.id, previous=None, at=at)
    db.refresh(schedule)
    assert schedule.last_sent_at is None


def test_failed_delivery_releases_claim_for_retry(db: Session) -> None:
    tz_name = "Europe/Minsk"
    _, schedule = _add_daily_schedule(
        db,
        tz_name=tz_name,
        time_of_day="20:30",
        channels=["telegram"],
    )
    user = db.get(User, schedule.user_id)
    assert user is not None
    user.telegram_user_id = 100_000 + uuid.uuid4().int % 1_000_000
    user.telegram_chat_id = 555
    user.telegram_linked_at = datetime.now(UTC)
    db.commit()
    now_utc = datetime(2026, 7, 15, 20, 31, tzinfo=ZoneInfo(tz_name)).astimezone(UTC)

    class FailingNotifier(FakeNotifier):
        def send(self, *, recipient: str, message: object) -> None:  # type: ignore[override]
            raise RuntimeError("telegram down")

    failing = NotificationDispatcher(
        {NotificationChannel.TELEGRAM: FailingNotifier(channel=NotificationChannel.TELEGRAM)}
    )
    stats = process_due_reminders(db, failing, now=now_utc)
    assert stats.daily_mood_sent == 0
    assert len(stats.errors) == 1
    db.refresh(schedule)
    assert schedule.last_sent_at is None

    tg = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    retry = process_due_reminders(
        db,
        NotificationDispatcher({NotificationChannel.TELEGRAM: tg}),
        now=now_utc + timedelta(minutes=5),
    )
    assert retry.daily_mood_sent == 1
    assert len(tg.outbox) == 1
