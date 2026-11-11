"""A pass that sends Telegram reminders first wakes the bot service (Render free sleeps)."""

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from app.config import settings
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.notifications import (
    EmailNotifier,
    FakeNotifier,
    NotificationChannel,
    NotificationDispatcher,
    process_due_reminders,
)
from app.services.notifications.bot_wakeup import wake_telegram_bot
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService

DUE_AT = datetime(2026, 7, 15, 20, 31, tzinfo=ZoneInfo("Europe/Minsk")).astimezone(UTC)


@pytest.fixture(autouse=True)
def _enable_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", True)
    monkeypatch.setattr(settings, "notifications_match_window_minutes", 30)
    monkeypatch.setattr(settings, "telegram_bot_health_url", "")


@pytest.fixture
def wakes(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []
    monkeypatch.setattr(
        "app.services.notifications.reminders.wake_telegram_bot", lambda: calls.append(1)
    )
    return calls


def _due_schedule(db: Session, *, channel: str) -> None:
    user = User(
        email=f"wake-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone="Europe/Minsk",
        email_verified_at=datetime.now(UTC),
    )
    if channel == "telegram":
        user.telegram_user_id = 100_000 + uuid.uuid4().int % 10**9
        user.telegram_chat_id = 4242
        user.telegram_linked_at = datetime.now(UTC)
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSchedule(
            user_id=user.id,
            kind="daily_mood",
            enabled=True,
            time_of_day="20:30",
            interval_days=1,
            channels=[channel],
        )
    )
    db.commit()


def test_telegram_pass_wakes_the_bot_once(db: Session, wakes: list[int]) -> None:
    _due_schedule(db, channel="telegram")
    _due_schedule(db, channel="telegram")
    telegram = FakeNotifier(channel=NotificationChannel.TELEGRAM)

    stats = process_due_reminders(
        db, NotificationDispatcher({NotificationChannel.TELEGRAM: telegram}), now=DUE_AT
    )

    assert stats.daily_mood_sent == 2
    assert wakes == [1]


def test_email_only_pass_does_not_wake_the_bot(db: Session, wakes: list[int]) -> None:
    _due_schedule(db, channel="email")
    mailer = FakeEmailService()

    process_due_reminders(
        db, NotificationDispatcher({NotificationChannel.EMAIL: EmailNotifier(mailer)}), now=DUE_AT
    )

    assert len(mailer.outbox) == 1
    assert wakes == []


def test_wake_is_off_without_a_url() -> None:
    assert wake_telegram_bot() is None


def test_wake_pings_in_the_background_and_swallows_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_health_url", "https://bot.example/health")
    calls: list[str] = []

    def failing_get(url: str, **_kwargs: object) -> None:
        calls.append(url)
        raise RuntimeError("cold start timeout")

    monkeypatch.setattr("app.services.notifications.bot_wakeup.httpx.get", failing_get)

    thread = wake_telegram_bot()
    assert thread is not None
    thread.join(timeout=5)

    assert calls == ["https://bot.example/health"]
