import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.models.goal import Goal
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.models.user_notification_settings import UserNotificationSettings
from app.services.notifications import (
    EmailNotifier,
    FakeNotifier,
    NotificationChannel,
    NotificationDispatcher,
    NotificationMessage,
    process_due_reminders,
)
from app.services.notifications.base import BaseNotifier
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def test_base_notifier_requires_channel_and_send() -> None:
    notifier = BaseNotifier()

    with pytest.raises(NotImplementedError):
        _ = notifier.channel

    with pytest.raises(NotImplementedError):
        notifier.send(
            recipient="user@example.com",
            message=NotificationMessage(subject="Hi", body="Hello"),
        )


def test_fake_notifier_records_outbox() -> None:
    notifier = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    message = NotificationMessage(subject="Reminder", body="Log your mood")

    sent = notifier.send(recipient="123456", message=message)

    assert sent.channel is NotificationChannel.TELEGRAM
    assert sent.recipient == "123456"
    assert sent.subject == "Reminder"
    assert sent.body == "Log your mood"
    assert notifier.outbox == [sent]

    notifier.clear_outbox()
    assert notifier.outbox == []


def test_email_notifier_uses_email_service() -> None:
    mailer = FakeEmailService()
    notifier = EmailNotifier(mailer)

    sent = notifier.send(
        recipient="user@example.com",
        message=NotificationMessage(subject="Ping", body="Hello", html_body="<p>Hello</p>"),
    )

    assert sent.channel is NotificationChannel.EMAIL
    assert len(mailer.outbox) == 1
    assert mailer.outbox[0].to == "user@example.com"
    assert mailer.outbox[0].subject == "Ping"
    assert mailer.outbox[0].body == "Hello"


def test_dispatcher_routes_to_email(db: Session) -> None:
    mailer = FakeEmailService()
    dispatcher = NotificationDispatcher(
        {NotificationChannel.EMAIL: EmailNotifier(mailer)},
    )
    user = User(email=f"disp-{uuid.uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()

    sent = dispatcher.send(
        user=user,
        channels=[NotificationChannel.EMAIL],
        message=NotificationMessage(subject="Hi", body="Body"),
    )

    assert len(sent) == 1
    assert sent[0].recipient == user.email
    assert mailer.outbox[0].subject == "Hi"


def test_daily_mood_reminder_message_includes_attribution_query() -> None:
    from app.services.notifications.base import NotificationChannel
    from app.services.notifications.messages import daily_mood_reminder_message

    message = daily_mood_reminder_message(channel=NotificationChannel.EMAIL)
    assert "from=email%3Adaily_mood_reminder" in message.body or (
        "from=email:daily_mood_reminder" in message.body
    )
    assert message.html_body is not None
    assert "email" in message.html_body and "daily_mood_reminder" in message.html_body
    assert message.metadata == {
        "type": "daily_mood_reminder",
        "channel": "email",
        "source": "email:daily_mood_reminder",
    }


def test_goal_reminder_message_includes_attribution_query() -> None:
    from app.services.notifications.base import NotificationChannel
    from app.services.notifications.messages import goal_reminder_message

    message = goal_reminder_message(
        channel=NotificationChannel.EMAIL,
        goal_labels=["Walk"],
    )
    assert "from=email%3Agoal_reminder" in message.body or (
        "from=email:goal_reminder" in message.body
    )
    assert message.html_body is not None
    assert "goal_reminder" in message.html_body
    assert message.metadata["source"] == "email:goal_reminder"


def test_notification_settings_api_get_and_patch(
    auth_client,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "notify-settings@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    get_response = auth_client.get("/v1/notification-settings", headers=headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["enabled"] is False
    assert body["channels"] == ["email"]
    assert body["daily_mood_reminder_enabled"] is False
    assert body["daily_mood_reminder_time"] is None
    assert body["goal_reminders_enabled"] is False

    patch_response = auth_client.patch(
        "/v1/notification-settings",
        headers=headers,
        json={
            "enabled": True,
            "daily_mood_reminder_enabled": True,
            "daily_mood_reminder_time": "20:30:00",
            "goal_reminders_enabled": True,
            "channels": ["email"],
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["enabled"] is True
    assert updated["daily_mood_reminder_enabled"] is True
    assert updated["daily_mood_reminder_time"] == "20:30:00"
    assert updated["goal_reminders_enabled"] is True


def test_notification_settings_require_time_when_reminders_enabled(
    auth_client,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "notify-time@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/notification-settings",
        headers=headers,
        json={
            "enabled": True,
            "daily_mood_reminder_enabled": True,
        },
    )
    assert response.status_code == 400
    assert "daily_mood_reminder_time" in response.json()["detail"]


def test_process_due_reminders_sends_daily_mood(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.notifications.reminders.settings.notifications_match_window_minutes",
        5,
    )
    tz_name = "Europe/Minsk"
    tz = ZoneInfo(tz_name)
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=tz)
    now_utc = local_now.astimezone(UTC)

    user = User(
        email=f"daily-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSettings(
            user_id=user.id,
            enabled=True,
            channels=["email"],
            daily_mood_reminder_enabled=True,
            daily_mood_reminder_time=time(20, 30),
            goal_reminders_enabled=False,
        )
    )
    db.commit()

    mailer = FakeEmailService()
    dispatcher = NotificationDispatcher(
        {NotificationChannel.EMAIL: EmailNotifier(mailer)},
    )
    stats = process_due_reminders(db, dispatcher, now=now_utc)

    assert stats.daily_mood_sent == 1
    assert len(mailer.outbox) == 1
    assert "log your mood" in mailer.outbox[0].subject.lower()

    # Second run same day must not resend
    mailer.clear_outbox()
    stats_again = process_due_reminders(db, dispatcher, now=now_utc)
    assert stats_again.daily_mood_sent == 0
    assert mailer.outbox == []


def test_process_due_reminders_skips_when_mood_already_logged(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.notifications.reminders.settings.notifications_match_window_minutes",
        5,
    )
    tz_name = "Europe/Minsk"
    tz = ZoneInfo(tz_name)
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=tz)
    now_utc = local_now.astimezone(UTC)

    user = User(
        email=f"logged-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSettings(
            user_id=user.id,
            enabled=True,
            channels=["email"],
            daily_mood_reminder_enabled=True,
            daily_mood_reminder_time=time(20, 30),
            goal_reminders_enabled=False,
        )
    )
    db.add(
        MoodEntry(
            user_id=user.id,
            recorded_at=local_now.astimezone(UTC) - timedelta(hours=1),
            score=3,
            note=None,
        )
    )
    db.commit()

    mailer = FakeEmailService()
    dispatcher = NotificationDispatcher(
        {NotificationChannel.EMAIL: EmailNotifier(mailer)},
    )
    stats = process_due_reminders(db, dispatcher, now=now_utc)

    assert stats.daily_mood_sent == 0
    assert mailer.outbox == []


def test_process_due_reminders_sends_goal_nudge(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.notifications.reminders.settings.notifications_match_window_minutes",
        5,
    )
    tz_name = "Europe/Minsk"
    tz = ZoneInfo(tz_name)
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=tz)
    now_utc = local_now.astimezone(UTC)

    user = User(
        email=f"goals-notify-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSettings(
            user_id=user.id,
            enabled=True,
            channels=["email"],
            daily_mood_reminder_enabled=False,
            daily_mood_reminder_time=time(20, 30),
            goal_reminders_enabled=True,
        )
    )
    db.add(
        Goal(
            user_id=user.id,
            slug="exercise",
            labels={"en": "Exercise", "ru": "Спорт"},
            times_per_week=3,
            starts_on=date(2026, 7, 1),
            sort_order=0,
            show_on_entry=True,
        )
    )
    db.commit()

    mailer = FakeEmailService()
    dispatcher = NotificationDispatcher(
        {NotificationChannel.EMAIL: EmailNotifier(mailer)},
    )
    stats = process_due_reminders(db, dispatcher, now=now_utc)

    assert stats.goal_reminders_sent == 1
    assert len(mailer.outbox) == 1
    assert "goals" in mailer.outbox[0].subject.lower()
    assert "Exercise" in mailer.outbox[0].body


def test_dispatcher_routes_to_telegram(db: Session) -> None:
    tg = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    dispatcher = NotificationDispatcher({NotificationChannel.TELEGRAM: tg})
    user = User(
        email=f"tg-disp-{uuid.uuid4()}@example.com",
        password_hash="hash",
        telegram_user_id=111,
        telegram_chat_id=222,
        telegram_linked_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()

    sent = dispatcher.send(
        user=user,
        channels=[NotificationChannel.TELEGRAM],
        message=NotificationMessage(subject="Ping", body="Hello TG"),
    )

    assert len(sent) == 1
    assert sent[0].recipient == "222"
    assert tg.outbox[0].body == "Hello TG"


def test_telegram_notifier_calls_bot_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.notifications.telegram import TelegramNotifier

    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"ok": True, "result": {}}

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr("app.services.notifications.telegram.httpx.post", fake_post)
    notifier = TelegramNotifier(bot_token="test-token")
    sent = notifier.send(
        recipient="999",
        message=NotificationMessage(subject="Subj", body="Body text"),
    )
    assert sent.recipient == "999"
    assert sent.body == "Body text"
    assert len(calls) == 1
    assert "bottest-token/sendMessage" in str(calls[0]["url"])


def test_daily_mood_reminder_message_telegram_is_plain() -> None:
    from app.services.notifications.messages import daily_mood_reminder_message

    message = daily_mood_reminder_message(channel=NotificationChannel.TELEGRAM)
    assert message.html_body is None
    assert (message.metadata or {}).get("source") == "telegram:daily_mood_reminder"
    assert "log your mood" in message.body.lower()


def test_process_due_reminders_sends_telegram(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.notifications.reminders.settings.notifications_match_window_minutes",
        5,
    )
    tz_name = "Europe/Minsk"
    tz = ZoneInfo(tz_name)
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=tz)
    now_utc = local_now.astimezone(UTC)

    user = User(
        email=f"tg-daily-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
        telegram_user_id=333,
        telegram_chat_id=444,
        telegram_linked_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSettings(
            user_id=user.id,
            enabled=True,
            channels=["telegram"],
            daily_mood_reminder_enabled=True,
            daily_mood_reminder_time=time(20, 30),
            goal_reminders_enabled=False,
        )
    )
    db.commit()

    tg = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    dispatcher = NotificationDispatcher({NotificationChannel.TELEGRAM: tg})
    stats = process_due_reminders(db, dispatcher, now=now_utc)

    assert stats.daily_mood_sent == 1
    assert len(tg.outbox) == 1
    assert tg.outbox[0].recipient == "444"


def test_process_due_reminders_skips_unlinked_telegram(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.notifications.reminders.settings.notifications_match_window_minutes",
        5,
    )
    tz_name = "Europe/Minsk"
    tz = ZoneInfo(tz_name)
    local_now = datetime(2026, 7, 15, 20, 30, 10, tzinfo=tz)
    now_utc = local_now.astimezone(UTC)

    user = User(
        email=f"tg-skip-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz_name,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    db.add(
        UserNotificationSettings(
            user_id=user.id,
            enabled=True,
            channels=["telegram"],
            daily_mood_reminder_enabled=True,
            daily_mood_reminder_time=time(20, 30),
            goal_reminders_enabled=False,
        )
    )
    db.commit()

    tg = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    dispatcher = NotificationDispatcher({NotificationChannel.TELEGRAM: tg})
    stats = process_due_reminders(db, dispatcher, now=now_utc)

    assert stats.daily_mood_sent == 0
    assert stats.skipped >= 1
    assert tg.outbox == []


def test_notification_settings_reject_telegram_without_link(
    auth_client,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"tg-ch-{uuid.uuid4()}@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = auth_client.patch(
        "/v1/notification-settings",
        headers=headers,
        json={"channels": ["email", "telegram"]},
    )
    assert response.status_code == 400
    assert "link" in response.json()["detail"].lower()
