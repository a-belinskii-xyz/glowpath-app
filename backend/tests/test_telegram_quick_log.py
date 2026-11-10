"""Logging a mood with one tap in the Telegram chat (GP-65)."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.config import settings
from app.core.telegram_quick_log import (
    CALLBACK_DATA_MAX_BYTES,
    QuickTap,
    decode_quick_tap,
    encode_quick_tap,
    question_part,
    telegram_client_key,
)
from app.models.mood_entry import MoodEntry
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services.mood_preferences_service import get_or_create_preferences
from app.services.notifications.messages import quick_log_keyboard
from app.services.storage import FakeStorage
from app.services.telegram_quick_log_service import handle_quick_tap
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login

SERVICE_HEADERS = {"X-Telegram-Bot-Service-Token": "test-service-token"}
TG_USER_ID = 880077
MESSAGE_ID = 4242
QUESTION = "Evening. How’s your mood?"
FACES = {1: "😢", 2: "😞", 3: "😐", 4: "🙂", 5: "😄"}


# --- callback data and message text (no database) ---


@pytest.mark.parametrize(
    ("tap", "data"),
    [
        (QuickTap(score=4), "q:4"),
        (QuickTap(score=1, token="abc_-9"), "q:1:abc_-9"),
        (QuickTap(score=None), "q:u"),
        (QuickTap(score=None, token="tok"), "q:u:tok"),
    ],
)
def test_quick_tap_round_trips(tap: QuickTap, data: str) -> None:
    assert encode_quick_tap(tap) == data
    assert decode_quick_tap(data) == tap


@pytest.mark.parametrize("data", ["w:score:4", "q:", "q:0", "q:6", "q:x", "q:4:", "q:4:a:b", "x:4"])
def test_foreign_or_broken_callback_data_is_rejected(data: str) -> None:
    assert decode_quick_tap(data) is None


def test_callback_data_fits_telegram_limit() -> None:
    reminder_token = "A" * 22  # secrets.token_urlsafe(16)
    assert len(encode_quick_tap(QuickTap(score=5, token=reminder_token)).encode()) <= 64
    # A token that would not fit is dropped rather than breaking the button.
    assert encode_quick_tap(QuickTap(score=5, token="x" * CALLBACK_DATA_MAX_BYTES)) == "q:5"


def test_question_part_drops_previous_confirmation() -> None:
    logged = f"{QUESTION}\n\n✓ Logged: 🙂 good · 21:40\n🏆 New achievement: First step"
    assert question_part(logged) == QUESTION
    assert question_part(QUESTION) == QUESTION
    assert question_part(None) == ""


def test_logged_keyboard_marks_the_choice_and_offers_note_and_undo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    entry_id = uuid.uuid4()
    markup = quick_log_keyboard(
        locale="ru",
        faces=FACES,
        token="tok",
        selected=4,
        entry_id=entry_id,
        can_undo=True,
    )
    faces_row, actions = markup["inline_keyboard"]
    assert [button["text"] for button in faces_row] == ["😢", "😞", "😐", "•🙂•", "😄"]
    assert faces_row[0]["callback_data"] == "q:1:tok"
    assert actions[0]["text"] == "✏️ Заметка и теги"
    assert actions[0]["web_app"]["url"].endswith(f"tgWebAppStartParam=edit_{entry_id.hex}")
    assert actions[1] == {"text": "↩️ Отменить", "callback_data": "q:u:tok"}

    without_undo = quick_log_keyboard(
        locale="ru", faces=FACES, selected=4, entry_id=entry_id, can_undo=False
    )
    assert [button["text"] for button in without_undo["inline_keyboard"][1]] == ["✏️ Заметка и теги"]


# --- API (database) ---


@pytest.fixture
def telegram_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "telegram_bot_username", "glowpath_test_bot")
    monkeypatch.setattr(settings, "telegram_bot_service_token", "test-service-token")
    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")


def _linked_user(auth_client: TestClient, mailer: FakeEmailService, db: Session) -> User:
    email = f"tg-quick-{uuid.uuid4()}@example.com"
    token = register_verify_and_login(auth_client, mailer, email)
    code = auth_client.post(
        "/v1/telegram/link-codes", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]
    linked = auth_client.post(
        "/v1/telegram/bot/link",
        headers=SERVICE_HEADERS,
        json={
            "code": code,
            "telegram_user_id": TG_USER_ID,
            "telegram_chat_id": TG_USER_ID,
            "locale": "en",
        },
    )
    assert linked.status_code == 200
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def _tap(
    auth_client: TestClient,
    data: str,
    *,
    message_text: str | None = QUESTION,
    telegram_user_id: int = TG_USER_ID,
    locale: str | None = "en",
) -> dict[str, Any]:
    response = auth_client.post(
        "/v1/telegram/bot/quick-log/tap",
        headers=SERVICE_HEADERS,
        json={
            "telegram_user_id": telegram_user_id,
            "chat_id": TG_USER_ID,
            "message_id": MESSAGE_ID,
            "data": data,
            "message_text": message_text,
            "locale": locale,
        },
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _entries(db: Session, user: User) -> list[MoodEntry]:
    db.expire_all()
    return list(db.scalars(select(MoodEntry).where(MoodEntry.user_id == user.id)).all())


def test_tap_requires_service_token(auth_client: TestClient, telegram_configured: None) -> None:
    response = auth_client.post(
        "/v1/telegram/bot/quick-log/tap",
        json={"telegram_user_id": 1, "chat_id": 1, "message_id": 1, "data": "q:4"},
    )
    assert response.status_code == 401


def test_prompt_has_question_faces_and_detail_button(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    prefs = get_or_create_preferences(db, user_id=user.id)
    prefs.score_styles = {
        **(prefs.score_styles or {}),
        "5": {"color": "#3b82f6", "icon_type": "emoji", "icon": "🤩"},
    }
    db.commit()

    response = auth_client.get(
        "/v1/telegram/bot/quick-log",
        headers=SERVICE_HEADERS,
        params={"telegram_user_id": TG_USER_ID},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "How are you right now?"
    faces_row, detail_row = body["reply_markup"]["inline_keyboard"]
    assert [button["text"] for button in faces_row] == ["😢", "😞", "😐", "🙂", "🤩"]
    assert [button["callback_data"] for button in faces_row] == [f"q:{s}" for s in range(1, 6)]
    assert detail_row[0]["text"] == "✏️ Log in detail"
    assert detail_row[0]["web_app"]["url"].endswith("tgWebAppStartParam=create")


def test_prompt_404_when_not_linked(auth_client: TestClient, telegram_configured: None) -> None:
    response = auth_client.get(
        "/v1/telegram/bot/quick-log",
        headers=SERVICE_HEADERS,
        params={"telegram_user_id": 990099},
    )
    assert response.status_code == 404


def test_tap_logs_mood_and_confirms_under_the_question(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)

    reply = _tap(auth_client, "q:4")

    entries = _entries(db, user)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.score == 4
    assert entry.source == "telegram:bot"
    assert entry.client_key == telegram_client_key(chat_id=TG_USER_ID, message_id=MESSAGE_ID)
    assert re.fullmatch(rf"{re.escape(QUESTION)}\n\n✓ Logged: 🙂 good · \d\d:\d\d", reply["text"])
    assert reply["toast"] == "Logged"
    assert reply["alert"] is False
    faces_row, actions = reply["reply_markup"]["inline_keyboard"]
    assert faces_row[3]["text"] == "•🙂•"
    assert actions[0]["web_app"]["url"].endswith(f"tgWebAppStartParam=edit_{entry.id.hex}")
    assert actions[1]["callback_data"] == "q:u"


def test_second_tap_changes_the_same_entry(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    first = _tap(auth_client, "q:4")

    changed = _tap(auth_client, "q:2", message_text=first["text"])

    entries = _entries(db, user)
    assert [entry.score for entry in entries] == [2]
    assert changed["text"].count("✓") == 1
    assert changed["text"].startswith(f"{QUESTION}\n\n✓ Logged: 😞 bad · ")
    assert changed["toast"] == "Mood changed"

    same = _tap(auth_client, "q:2", message_text=changed["text"])
    assert same["toast"] is None
    assert same["text"] == changed["text"]
    assert len(_entries(db, user)) == 1


def test_reminder_tap_counts_as_answer_to_that_reminder(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    schedule = db.scalar(
        select(UserNotificationSchedule).where(
            UserNotificationSchedule.user_id == user.id,
            UserNotificationSchedule.kind == "daily_mood",
        )
    )
    assert schedule is not None  # provisioned at sign-up
    delivery = NotificationDelivery(
        user_id=user.id,
        schedule_id=schedule.id,
        kind="daily_mood",
        channels=["telegram"],
        token="remindertok",
    )
    db.add(delivery)
    db.commit()

    reply = _tap(auth_client, "q:5:remindertok")

    entry = _entries(db, user)[0]
    assert entry.source == "telegram:daily_mood_reminder"
    db.refresh(delivery)
    assert delivery.engaged_at is not None
    faces_row = reply["reply_markup"]["inline_keyboard"][0]
    assert faces_row[0]["callback_data"] == "q:1:remindertok"


def test_undo_removes_fresh_entry_and_brings_the_question_back(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    logged = _tap(auth_client, "q:3")

    undone = _tap(auth_client, "q:u", message_text=logged["text"])

    assert _entries(db, user) == []
    assert undone["text"] == QUESTION
    assert undone["toast"] == "Entry removed"
    faces_row, detail_row = undone["reply_markup"]["inline_keyboard"]
    assert [button["text"] for button in faces_row] == list(FACES.values())
    assert detail_row[0]["text"] == "✏️ Log in detail"

    # A second tap on Undo (or a message whose entry is gone) just shows the question.
    again = _tap(auth_client, "q:u", message_text=undone["text"])
    assert again["text"] == QUESTION
    assert again["toast"] is None

    # The same message can log again after an undo.
    _tap(auth_client, "q:5", message_text=undone["text"])
    assert [entry.score for entry in _entries(db, user)] == [5]


def test_undo_is_refused_after_the_window(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    logged = _tap(auth_client, "q:3")

    reply = handle_quick_tap(
        db,
        telegram_user_id=TG_USER_ID,
        chat_id=TG_USER_ID,
        message_id=MESSAGE_ID,
        data="q:u",
        message_text=logged["text"],
        locale="en",
        storage=FakeStorage(),
        now=datetime.now(UTC) + timedelta(minutes=11),
    )

    assert len(_entries(db, user)) == 1
    assert reply.toast == "You can delete this entry in the app now"
    assert reply.reply_markup is not None
    actions = reply.reply_markup["inline_keyboard"][1]
    assert [button.get("callback_data") for button in actions] == [None]


def test_undo_keeps_an_entry_with_a_note(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    logged = _tap(auth_client, "q:3")
    entry = _entries(db, user)[0]
    entry.note = "Written in the app"
    db.commit()

    reply = _tap(auth_client, "q:u", message_text=logged["text"])

    assert len(_entries(db, user)) == 1
    assert reply["toast"] == "You can delete this entry in the app now"
    assert "q:u" not in str(reply["reply_markup"])


def test_tap_from_unlinked_account_points_to_the_app(
    auth_client: TestClient,
    telegram_configured: None,
) -> None:
    reply = _tap(auth_client, "q:4", telegram_user_id=990099, locale="ru-RU")

    assert reply["text"] == "Сначала открой GlowPath. Настройка займёт около минуты."
    button = reply["reply_markup"]["inline_keyboard"][0][0]
    assert button["text"] == "Открыть GlowPath"
    assert button["web_app"]["url"].endswith("tgWebAppStartParam=onboarding")


def test_unknown_button_only_shows_an_alert(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)

    reply = _tap(auth_client, "q:9")

    assert reply["text"] is None
    assert reply["alert"] is True
    assert "/log" in reply["toast"]
    assert _entries(db, user) == []


def test_confirmation_uses_language_labels_and_clock_of_the_person(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    user.locale = "ru"
    user.time_format = "12h"
    prefs = get_or_create_preferences(db, user_id=user.id)
    prefs.score_styles = {
        **(prefs.score_styles or {}),
        "4": {**(prefs.score_styles or {}).get("4", {}), "label": "норм"},
    }
    db.commit()

    reply = _tap(auth_client, "q:4", message_text=None)

    assert re.fullmatch(
        r"Как ты сейчас\?\n\n✓ Записано: 🙂 норм · \d{1,2}:\d\d [AP]M", reply["text"]
    )
    assert reply["toast"] == "Записано"


def test_confirmation_names_a_new_achievement(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import telegram_quick_log_service

    real_create = telegram_quick_log_service.create_mood_entry

    def create_with_achievement(*args: Any, **kwargs: Any) -> tuple[MoodEntry, list[Any]]:
        entry, _unlocked = real_create(*args, **kwargs)
        return entry, [{"name": "First step"}]

    monkeypatch.setattr(telegram_quick_log_service, "create_mood_entry", create_with_achievement)
    _linked_user(auth_client, mailer, db)

    reply = _tap(auth_client, "q:4")

    assert reply["text"].endswith("\n🏆 New achievement: First step")


def test_one_entry_per_message_is_enforced_by_the_database(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
    telegram_configured: None,
) -> None:
    user = _linked_user(auth_client, mailer, db)
    _tap(auth_client, "q:4")
    key = telegram_client_key(chat_id=TG_USER_ID, message_id=MESSAGE_ID)

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            MoodEntry(
                user_id=user.id,
                score=3,
                score_color="#eab308",
                recorded_at=datetime.now(UTC),
                client_key=key,
            )
        )
        db.flush()

    count = db.scalar(
        select(func.count()).select_from(MoodEntry).where(MoodEntry.client_key == key)
    )
    assert count == 1
