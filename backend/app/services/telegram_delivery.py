"""Send a file from the bot into the user's own Telegram chat."""

from __future__ import annotations

import httpx

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.user import User

TELEGRAM_API = "https://api.telegram.org"


class TelegramDeliveryError(AppError):
    pass


def ensure_can_deliver(user: User) -> str:
    """Raise unless the bot can reach this user's chat; return the bot token."""
    if user.telegram_chat_id is None:
        raise TelegramDeliveryError(
            "Telegram is not linked",
            code=ErrorCode.TELEGRAM_NOT_LINKED,
            status_code=409,
        )
    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        raise TelegramDeliveryError(
            "Telegram bot token is not configured",
            code=ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED,
            status_code=503,
        )
    return bot_token


def send_to_user_chat(
    *,
    user: User,
    method: str,
    field: str,
    filename: str,
    data: bytes,
    content_type: str,
    caption: str | None = None,
    timeout: float = 30.0,
) -> None:
    """Call a Bot API upload method (``sendPhoto``, ``sendDocument``) for the user's chat."""
    bot_token = ensure_can_deliver(user)
    form = {"chat_id": str(user.telegram_chat_id)}
    if caption:
        form["caption"] = caption
    url = f"{TELEGRAM_API}/bot{bot_token}/{method}"
    try:
        response = httpx.post(
            url,
            data=form,
            files={field: (filename, data, content_type)},
            timeout=timeout,
        )
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TelegramDeliveryError(
            f"Failed to call Telegram {method}: {exc}",
            code=ErrorCode.TELEGRAM_SEND_FAILED,
            status_code=502,
        ) from exc

    if not isinstance(payload, dict) or not payload.get("ok"):
        # Typically 403 "bot was blocked by the user" or a chat that never started the bot.
        raise TelegramDeliveryError(
            f"Telegram API rejected {method}: {payload}",
            code=ErrorCode.TELEGRAM_SEND_REJECTED,
            status_code=502,
        )
