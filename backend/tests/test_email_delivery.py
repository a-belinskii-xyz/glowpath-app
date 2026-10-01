import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from app.config import settings
from app.core.security import create_access_token, create_email_unsubscribe_token
from app.models.user import User
from app.models.user_notification_schedule import UserNotificationSchedule
from app.services import email_service as email_module
from app.services.email_service import EmailSendError, EmailService
from app.services.notifications import EmailNotifier, NotificationChannel
from app.services.notifications.messages import daily_mood_reminder_message
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

UNSUBSCRIBE_URL = "/v1/notification-settings/unsubscribe"


class _RecordingEmailService(EmailService):
    def __init__(self) -> None:
        super().__init__()
        self.headers: Mapping[str, str] | None = None

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        del to, subject, body, html_body
        self.headers = headers


def _user_with_schedules(db: Session, *channel_sets: list[str]) -> User:
    user = User(
        email=f"unsub-{uuid.uuid4()}@example.com",
        password_hash="hash",
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    for index, channels in enumerate(channel_sets):
        db.add(
            UserNotificationSchedule(
                user_id=user.id,
                kind=["daily_mood", "goal_tracking"][index],
                enabled=True,
                time_of_day="21:00",
                interval_days=1,
                channels=channels,
            )
        )
    db.commit()
    return user


def test_resend_api_is_used_when_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(200, json={"id": "email-id"})

    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "email_from", "GlowPath <hello@mail.example.com>")
    monkeypatch.setattr(email_module.httpx, "post", fake_post)

    EmailService().send(
        to="user@example.com",
        subject="Hi",
        body="text",
        html_body="<p>text</p>",
        headers={"List-Unsubscribe": "<https://example.com/u>"},
    )

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == email_module.RESEND_API_URL
    assert call["headers"] == {"Authorization": "Bearer re_test"}
    assert call["json"] == {
        "from": "GlowPath <hello@mail.example.com>",
        "to": ["user@example.com"],
        "subject": "Hi",
        "text": "text",
        "html": "<p>text</p>",
        "headers": {"List-Unsubscribe": "<https://example.com/u>"},
    }


def test_resend_rejection_raises_send_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(
        email_module.httpx,
        "post",
        lambda url, **kwargs: httpx.Response(422, json={"message": "bad from"}),
    )
    with pytest.raises(EmailSendError):
        EmailService().send(to="user@example.com", subject="Hi", body="text")


def test_reminder_email_carries_unsubscribe_link_and_headers() -> None:
    user_id = uuid.uuid4()
    token = create_email_unsubscribe_token(user_id)
    message = daily_mood_reminder_message(
        channel=NotificationChannel.EMAIL,
        locale="ru",
        unsubscribe_token=token,
    )
    assert f"/unsubscribe?token={token}" in message.body
    assert "Отписаться от писем" in (message.html_body or "")

    mailer = _RecordingEmailService()
    EmailNotifier(mailer).send(recipient="user@example.com", message=message)
    assert mailer.headers is not None
    assert mailer.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert (
        f"/v1/notification-settings/unsubscribe?token={token}"
        in (mailer.headers["List-Unsubscribe"])
    )


def test_telegram_reminder_has_no_unsubscribe_footer() -> None:
    message = daily_mood_reminder_message(channel=NotificationChannel.TELEGRAM)
    assert "unsubscribe" not in message.body.lower()
    assert "email_headers" not in (message.metadata or {})


def test_unsubscribe_turns_off_email_only_and_keeps_telegram(
    auth_client: TestClient,
    db: Session,
) -> None:
    user = _user_with_schedules(db, ["email"], ["email", "telegram"])
    token = create_email_unsubscribe_token(user.id)

    response = auth_client.post(UNSUBSCRIBE_URL, params={"token": token})

    assert response.status_code == 200
    assert response.json() == {"unsubscribed": True}
    rows = {
        row.kind: row for row in db.query(UserNotificationSchedule).filter_by(user_id=user.id).all()
    }
    assert rows["daily_mood"].enabled is False
    assert rows["daily_mood"].channels == ["email"]
    assert rows["goal_tracking"].enabled is True
    assert rows["goal_tracking"].channels == ["telegram"]


def test_one_click_unsubscribe_accepts_form_post(auth_client: TestClient, db: Session) -> None:
    user = _user_with_schedules(db, ["email"])
    token = create_email_unsubscribe_token(user.id)

    response = auth_client.post(
        UNSUBSCRIBE_URL,
        params={"token": token},
        data={"List-Unsubscribe": "One-Click"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize("make_token", [lambda _: "garbage", create_access_token])
def test_unsubscribe_rejects_foreign_tokens(
    auth_client: TestClient,
    db: Session,
    make_token: Any,
) -> None:
    user = _user_with_schedules(db, ["email"])
    response = auth_client.post(UNSUBSCRIBE_URL, params={"token": make_token(user.id)})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_token"
