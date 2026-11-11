"""F0.5: the reminder tick skips the database until the next reminder can be due."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.config import settings
from app.db.session import engine as app_engine
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.notifications import (
    BaseNotifier,
    EmailNotifier,
    NotificationChannel,
    NotificationDispatcher,
    NotificationMessage,
    SentNotification,
)
from app.services.notifications.due_cache import (
    DueCache,
    compute_next_due_at,
    next_reminder_at,
    reminder_due_cache,
)
from app.services.notifications.telegram import TelegramNotifier
from app.services.notifications.tick import ReminderTickOutcome, run_reminder_tick
from app.services.notifications.worker_status import record_heartbeat, system_status
from fastapi.testclient import TestClient
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

CRON_SECRET = "test-cron-secret"
TICK_URL = "/v1/internal/reminders/tick"
MINSK = ZoneInfo("Europe/Minsk")
BERLIN = ZoneInfo("Europe/Berlin")


@pytest.fixture(autouse=True)
def _enable_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", True)
    monkeypatch.setattr(settings, "notifications_worker_enabled", True)
    monkeypatch.setattr(settings, "notifications_match_window_minutes", 30)
    monkeypatch.setattr(settings, "notifications_due_cache_ttl_seconds", 6 * 3600)
    monkeypatch.setattr(settings, "reminders_cron_secret", CRON_SECRET)


@contextmanager
def _recorded_sql(db: Session) -> Iterator[list[str]]:
    """Every statement sent through the test connection or the app's own engine."""
    statements: list[str] = []

    def record(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement)

    targets: list[Any] = [db.get_bind(), app_engine]
    for target in targets:
        event.listen(target, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        for target in targets:
            event.remove(target, "before_cursor_execute", record)


def _user(db: Session, *, tz: str = "Europe/Minsk", telegram: bool = False) -> User:
    user = User(
        email=f"due-{uuid.uuid4()}@example.com",
        password_hash="hash",
        timezone=tz,
        email_verified_at=datetime.now(UTC),
    )
    if telegram:
        user.telegram_user_id = 100_000 + uuid.uuid4().int % 10**9
        user.telegram_chat_id = 4242
        user.telegram_linked_at = datetime.now(UTC)
    db.add(user)
    db.flush()
    return user


def _schedule(
    db: Session,
    user: User,
    *,
    time_of_day: str = "20:30",
    channels: list[str] | None = None,
    days_of_week: list[int] | None = None,
    enabled: bool = True,
    paused_at: datetime | None = None,
) -> UserNotificationSchedule:
    schedule = UserNotificationSchedule(
        user_id=user.id,
        kind="daily_mood",
        enabled=enabled,
        time_of_day=time_of_day,
        interval_days=1,
        days_of_week=days_of_week,
        channels=channels if channels is not None else ["email"],
        paused_at=paused_at,
    )
    db.add(schedule)
    db.commit()
    return schedule


def _email(mailer: FakeEmailService) -> NotificationDispatcher:
    return NotificationDispatcher({NotificationChannel.EMAIL: EmailNotifier(mailer)})


def _tick(db: Session, dispatcher: NotificationDispatcher, at: datetime) -> Any:
    return run_reminder_tick(db, dispatcher, now=at, due_cache=reminder_due_cache)


def _minsk(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, second, tzinfo=MINSK).astimezone(UTC)


# --- next_reminder_at: pure date arithmetic ------------------------------------------


def _next(after: datetime, **overrides: Any) -> datetime | None:
    params: dict[str, Any] = {
        "time_of_day": time(20, 30),
        "tz": MINSK,
        "days_of_week": None,
        "interval_days": 1,
        "last_sent_at": None,
    }
    params.update(overrides)
    return next_reminder_at(after=after, **params)


def test_next_reminder_is_later_today_in_the_users_zone() -> None:
    assert _next(_minsk(15, 12, 0)) == _minsk(15, 20, 30)


def test_next_reminder_after_todays_window_opened_is_tomorrow() -> None:
    assert _next(_minsk(15, 20, 30)) == _minsk(16, 20, 30)
    assert _next(_minsk(15, 21, 0)) == _minsk(16, 20, 30)


def test_next_reminder_skips_days_not_in_days_of_week() -> None:
    # 15.07.2026 is a Wednesday; only Mondays are allowed.
    assert _next(_minsk(15, 12, 0), days_of_week=[0]) == _minsk(20, 20, 30)


def test_next_reminder_respects_interval_after_last_send() -> None:
    sent = _minsk(15, 20, 31)
    assert _next(_minsk(15, 21, 0), interval_days=3, last_sent_at=sent) == _minsk(18, 20, 30)


def test_next_reminder_crosses_the_october_dst_switch() -> None:
    # Berlin leaves summer time on Sunday 25.10.2026: 09:00 is 07:00 UTC, then 08:00 UTC.
    after = datetime(2026, 10, 24, 10, 0, tzinfo=BERLIN).astimezone(UTC)
    result = _next(after, time_of_day=time(9, 0), tz=BERLIN)
    assert result == datetime(2026, 10, 25, 8, 0, tzinfo=UTC)


def test_next_reminder_takes_the_first_of_two_repeated_wall_times() -> None:
    after = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    result = _next(after, time_of_day=time(2, 30), tz=BERLIN)
    assert result == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)


def test_next_reminder_in_a_skipped_hour_is_never_late() -> None:
    # 02:30 does not exist on 29.03.2026 in Berlin; an early wake-up is fine.
    after = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    result = _next(after, time_of_day=time(2, 30), tz=BERLIN)
    assert result is not None
    assert result <= datetime(2026, 3, 29, 1, 30, tzinfo=UTC)


# --- compute_next_due_at: one query over all schedules -------------------------------


def test_compute_next_due_at_takes_the_earliest_enabled_schedule(db: Session) -> None:
    _schedule(db, _user(db), time_of_day="21:00")
    _schedule(db, _user(db, tz="UTC"), time_of_day="17:45")  # 20:45 in Minsk
    _schedule(db, _user(db), time_of_day="20:10", enabled=False)
    _schedule(db, _user(db), time_of_day="20:20", paused_at=datetime.now(UTC))

    assert compute_next_due_at(db, after=_minsk(15, 20, 0)) == _minsk(15, 20, 45)


def test_compute_next_due_at_without_schedules_is_none(db: Session) -> None:
    assert compute_next_due_at(db, after=_minsk(15, 20, 0)) is None


# --- DueCache ------------------------------------------------------------------------


def test_cache_drops_a_snapshot_computed_before_an_invalidation() -> None:
    cache = DueCache()
    now = datetime(2026, 7, 15, tzinfo=UTC)
    generation = cache.generation
    cache.invalidate()  # a settings change lands while a pass is computing

    stored = cache.store(
        next_due_at=now + timedelta(hours=1), computed_at=now, generation=generation
    )

    assert stored is False
    assert cache.idle_snapshot(now, ttl=timedelta(hours=6)) is None


def test_cache_is_idle_only_before_next_due_and_within_ttl() -> None:
    cache = DueCache()
    now = datetime(2026, 7, 15, tzinfo=UTC)
    ttl = timedelta(hours=6)
    cache.store(next_due_at=now + timedelta(hours=1), computed_at=now, generation=cache.generation)

    assert cache.idle_snapshot(now + timedelta(minutes=59), ttl=ttl) is not None
    assert cache.idle_snapshot(now + timedelta(hours=1), ttl=ttl) is None

    cache.store(next_due_at=None, computed_at=now, generation=cache.generation)
    assert cache.idle_snapshot(now + timedelta(hours=5), ttl=ttl) is not None
    assert cache.idle_snapshot(now + ttl, ttl=ttl) is None


# --- the tick ------------------------------------------------------------------------


def test_cold_start_runs_a_pass_then_idles_without_sql(
    db: Session, mailer: FakeEmailService
) -> None:
    _schedule(db, _user(db))

    with _recorded_sql(db) as pass_statements:
        first = _tick(db, _email(mailer), _minsk(15, 20, 0))
    assert first.outcome is ReminderTickOutcome.DONE
    assert first.next_due_at == _minsk(15, 20, 30)
    assert pass_statements  # the recorder does see the queries of a full pass

    with _recorded_sql(db) as statements:
        second = _tick(db, _email(mailer), _minsk(15, 20, 5))
    assert second.outcome is ReminderTickOutcome.IDLE
    assert second.next_due_at == _minsk(15, 20, 30)
    assert statements == []


def test_reminder_goes_out_once_when_its_time_comes(db: Session, mailer: FakeEmailService) -> None:
    _schedule(db, _user(db))
    _tick(db, _email(mailer), _minsk(15, 20, 0))

    due = _tick(db, _email(mailer), _minsk(15, 20, 30, 10))
    assert due.outcome is ReminderTickOutcome.DONE
    assert due.stats.daily_mood_sent == 1
    assert due.next_due_at == _minsk(16, 20, 30)

    after = _tick(db, _email(mailer), _minsk(15, 20, 35))
    assert after.outcome is ReminderTickOutcome.IDLE
    assert len(mailer.outbox) == 1


def test_days_of_week_push_next_due_to_the_next_allowed_day(
    db: Session, mailer: FakeEmailService
) -> None:
    _schedule(db, _user(db), days_of_week=[0])  # Mondays only; 15.07.2026 is a Wednesday

    result = _tick(db, _email(mailer), _minsk(15, 12, 0))

    assert result.next_due_at == _minsk(20, 20, 30)


def test_reminder_arrives_on_time_across_the_dst_switch(
    db: Session, mailer: FakeEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The snapshot is taken the day before, so let it outlive the default TTL.
    monkeypatch.setattr(settings, "notifications_due_cache_ttl_seconds", 48 * 3600)
    _schedule(db, _user(db, tz="Europe/Berlin"), time_of_day="09:00")
    switch_day = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)  # 09:00 CET

    first = _tick(db, _email(mailer), datetime(2026, 10, 24, 10, 0, tzinfo=BERLIN))
    assert first.next_due_at == switch_day
    before = _tick(db, _email(mailer), switch_day - timedelta(minutes=1))
    assert before.outcome is ReminderTickOutcome.IDLE

    due = _tick(db, _email(mailer), switch_day + timedelta(seconds=30))
    assert due.outcome is ReminderTickOutcome.DONE
    assert due.stats.daily_mood_sent == 1


def test_failed_delivery_is_retried_on_the_next_tick(db: Session, mailer: FakeEmailService) -> None:
    _schedule(db, _user(db))

    class FailingEmail(BaseNotifier):
        @property
        def channel(self) -> NotificationChannel:
            return NotificationChannel.EMAIL

        def send(self, *, recipient: str, message: NotificationMessage) -> SentNotification:
            raise RuntimeError("smtp down")

    at = _minsk(15, 20, 31)
    failed = _tick(db, NotificationDispatcher({NotificationChannel.EMAIL: FailingEmail()}), at)
    assert failed.stats.released_claims == 1
    assert failed.next_due_at == at

    retry = _tick(db, _email(mailer), _minsk(15, 20, 36))
    assert retry.outcome is ReminderTickOutcome.DONE
    assert retry.stats.daily_mood_sent == 1


def test_ttl_forces_a_fresh_pass(
    db: Session, mailer: FakeEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "notifications_due_cache_ttl_seconds", 3600)
    _schedule(db, _user(db), time_of_day="23:00")

    _tick(db, _email(mailer), _minsk(15, 12, 0))
    assert _tick(db, _email(mailer), _minsk(15, 12, 59)).outcome is ReminderTickOutcome.IDLE
    assert _tick(db, _email(mailer), _minsk(15, 13, 0)).outcome is ReminderTickOutcome.DONE


def test_no_schedules_means_idle_until_something_changes(
    db: Session, mailer: FakeEmailService
) -> None:
    first = _tick(db, _email(mailer), _minsk(15, 12, 0))
    assert first.outcome is ReminderTickOutcome.DONE
    assert first.next_due_at is None
    assert _tick(db, _email(mailer), _minsk(15, 12, 5)).outcome is ReminderTickOutcome.IDLE

    _schedule(db, _user(db), time_of_day="12:00")
    catch_up = _tick(db, _email(mailer), _minsk(15, 12, 10))
    assert catch_up.outcome is ReminderTickOutcome.DONE
    assert catch_up.stats.daily_mood_sent == 1


def test_disabled_feature_answers_without_sql(
    db: Session, mailer: FakeEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "feature_notifications_enabled", False)
    with _recorded_sql(db) as statements:
        result = _tick(db, _email(mailer), _minsk(15, 12, 0))
    assert result.outcome is ReminderTickOutcome.FEATURE_DISABLED
    assert statements == []


def test_telegram_reminder_after_idle_ticks_keeps_the_mood_buttons(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    payloads: list[dict[str, Any]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"ok": True, "result": {}}

    def fake_post(url: str, *, json: dict[str, Any], **_kwargs: object) -> FakeResponse:
        payloads.append(json)
        return FakeResponse()

    monkeypatch.setattr("app.services.notifications.telegram.httpx.post", fake_post)
    _schedule(db, _user(db, telegram=True), channels=["telegram"])
    _schedule(db, _user(db, telegram=True), channels=["telegram"])
    dispatcher = NotificationDispatcher(
        {NotificationChannel.TELEGRAM: TelegramNotifier(bot_token="test-token")}
    )
    _tick(db, dispatcher, _minsk(15, 20, 0))
    assert _tick(db, dispatcher, _minsk(15, 20, 25)).outcome is ReminderTickOutcome.IDLE

    due = _tick(db, dispatcher, _minsk(15, 20, 31))

    assert due.stats.daily_mood_sent == 2
    assert len(payloads) == 2
    for payload in payloads:
        faces = payload["reply_markup"]["inline_keyboard"][0]
        assert len(faces) == 5
        assert all(button["callback_data"].startswith("q:") for button in faces)


# --- invalidation --------------------------------------------------------------------


def _prime_cache() -> None:
    now = datetime.now(UTC)
    reminder_due_cache.store(
        next_due_at=now + timedelta(days=1),
        computed_at=now,
        generation=reminder_due_cache.generation,
    )
    assert reminder_due_cache.snapshot is not None


def test_settings_change_through_the_api_resets_the_cache(
    auth_client: TestClient, mailer: FakeEmailService
) -> None:
    token = register_verify_and_login(auth_client, mailer, f"due-{uuid.uuid4()}@example.com")
    _prime_cache()

    response = auth_client.patch(
        "/v1/notification-settings/daily_mood",
        headers={"Authorization": f"Bearer {token}"},
        json={"enabled": True, "time_of_day": "07:15"},
    )

    assert response.status_code == 200
    assert reminder_due_cache.snapshot is None


def test_timezone_change_resets_the_cache(db: Session) -> None:
    user = _user(db)
    db.commit()
    _prime_cache()

    user.timezone = "Asia/Tokyo"
    db.commit()

    assert reminder_due_cache.snapshot is None


def test_unrelated_user_change_keeps_the_cache(db: Session) -> None:
    user = _user(db)
    db.commit()
    _prime_cache()

    user.display_name = "Someone"
    db.commit()

    assert reminder_due_cache.snapshot is not None


def test_bulk_schedule_update_resets_the_cache(db: Session) -> None:
    schedule = _schedule(db, _user(db))
    _prime_cache()

    db.execute(
        update(UserNotificationSchedule)
        .where(UserNotificationSchedule.id == schedule.id)
        .values(time_of_day="06:00")
    )
    db.commit()

    assert reminder_due_cache.snapshot is None


def test_rolled_back_change_keeps_the_cache(db: Session) -> None:
    schedule = _schedule(db, _user(db))
    _prime_cache()

    schedule.time_of_day = "06:00"
    db.flush()
    db.rollback()

    assert reminder_due_cache.snapshot is not None


# --- HTTP endpoint and status --------------------------------------------------------


def test_http_tick_reports_next_due_and_then_idles_without_sql(
    auth_client: TestClient, db: Session
) -> None:
    from app.api.v1.internal import get_notification_dispatcher
    from app.main import app

    later = (datetime.now(UTC) + timedelta(hours=3)).replace(second=0, microsecond=0)
    _schedule(db, _user(db, tz="UTC"), time_of_day=later.strftime("%H:%M"))
    app.dependency_overrides[get_notification_dispatcher] = lambda: _email(FakeEmailService())
    headers = {"Authorization": f"Bearer {CRON_SECRET}"}

    first = auth_client.post(TICK_URL, headers=headers)
    assert first.status_code == 200
    assert first.json()["outcome"] == "done"
    assert datetime.fromisoformat(first.json()["next_due_at"]) == later

    with _recorded_sql(db) as statements:
        second = auth_client.post(TICK_URL, headers=headers)
    assert second.status_code == 200
    assert second.json()["outcome"] == "idle"
    assert datetime.fromisoformat(second.json()["next_due_at"]) == later
    assert statements == []


def test_status_counts_a_recent_idle_tick_as_alive(db: Session) -> None:
    now = datetime.now(UTC)
    record_heartbeat(db, meta={"phase": "done"}, at=now - timedelta(hours=2))
    assert system_status(db, now=now).status_code == "WORKER_OFFLINE"

    reminder_due_cache.note_tick(now - timedelta(seconds=30))

    status = system_status(db, now=now)
    assert status.status_code == "OK"
    assert status.worker_status == "healthy"
