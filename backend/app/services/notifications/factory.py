from __future__ import annotations

from app.config import settings
from app.services.email_service import EmailService, email_service
from app.services.notifications.base import BaseNotifier, NotificationChannel
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.email import EmailNotifier
from app.services.notifications.telegram import TelegramNotifier


def build_notification_dispatcher(
    mailer: EmailService | None = None,
    *,
    telegram_bot_token: str | None = None,
) -> NotificationDispatcher:
    """Build the default channel dispatcher (email + Telegram when configured)."""
    service = mailer if mailer is not None else email_service
    notifiers: dict[NotificationChannel, BaseNotifier] = {
        NotificationChannel.EMAIL: EmailNotifier(service),
    }
    token = (
        telegram_bot_token if telegram_bot_token is not None else settings.telegram_bot_token
    ).strip()
    if token:
        notifiers[NotificationChannel.TELEGRAM] = TelegramNotifier(bot_token=token)
    return NotificationDispatcher(notifiers)


notification_dispatcher = build_notification_dispatcher()
