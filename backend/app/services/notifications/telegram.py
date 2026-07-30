from __future__ import annotations

import httpx

from app.config import settings
from app.core.error_codes import ErrorCode
from app.services.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationError,
    NotificationMessage,
    SentNotification,
)

TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier(BaseNotifier):
    """Delivers notifications via the Telegram Bot API ``sendMessage``."""

    def __init__(self, *, bot_token: str | None = None) -> None:
        raw = bot_token if bot_token is not None else settings.telegram_bot_token
        self._bot_token = raw.strip()

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.TELEGRAM

    def send(self, *, recipient: str, message: NotificationMessage) -> SentNotification:
        if not self._bot_token:
            raise NotificationError(
                "Telegram bot token is not configured",
                code=ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED,
                status_code=503,
            )
        if not recipient.strip():
            raise NotificationError(
                "Telegram recipient is empty",
                code=ErrorCode.TELEGRAM_RECIPIENT_EMPTY,
                status_code=400,
            )

        text = message.body.strip() or message.subject
        url = f"{TELEGRAM_API}/bot{self._bot_token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={"chat_id": recipient, "text": text, "disable_web_page_preview": False},
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise NotificationError(
                f"Failed to send Telegram notification: {exc}",
                code=ErrorCode.TELEGRAM_SEND_FAILED,
                status_code=502,
            ) from exc

        if not isinstance(payload, dict) or not payload.get("ok"):
            raise NotificationError(
                f"Telegram API rejected sendMessage: {payload}",
                code=ErrorCode.TELEGRAM_SEND_REJECTED,
                status_code=502,
            )

        return SentNotification(
            channel=NotificationChannel.TELEGRAM,
            recipient=recipient,
            subject=message.subject,
            body=text,
        )
