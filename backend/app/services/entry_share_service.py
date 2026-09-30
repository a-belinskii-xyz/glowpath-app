"""Deliver a client-rendered entry share image to the user's Telegram chat.

The Mini App cannot always hand a file to the phone's share sheet, so the bot
sends the picture into the user's chat instead; from there it can be forwarded
or saved to the gallery.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.user import User

TELEGRAM_API = "https://api.telegram.org"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Telegram's sendPhoto accepts photos up to 10 MB.
SHARE_IMAGE_MAX_BYTES = 10 * 1024 * 1024


class EntryShareError(AppError):
    pass


def validate_share_image(data: bytes) -> None:
    if not data.startswith(PNG_SIGNATURE):
        raise EntryShareError(
            "Share image must be a PNG file",
            code=ErrorCode.SHARE_IMAGE_INVALID,
            status_code=400,
        )
    if len(data) > SHARE_IMAGE_MAX_BYTES:
        raise EntryShareError(
            "Share image is too large",
            code=ErrorCode.SHARE_IMAGE_INVALID,
            status_code=413,
            params={"max_mb": str(SHARE_IMAGE_MAX_BYTES // (1024 * 1024))},
        )


def send_share_image_to_telegram(*, user: User, data: bytes, filename: str) -> None:
    validate_share_image(data)
    if user.telegram_chat_id is None:
        raise EntryShareError(
            "Telegram is not linked",
            code=ErrorCode.TELEGRAM_NOT_LINKED,
            status_code=409,
        )
    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        raise EntryShareError(
            "Telegram bot token is not configured",
            code=ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED,
            status_code=503,
        )

    url = f"{TELEGRAM_API}/bot{bot_token}/sendPhoto"
    try:
        response = httpx.post(
            url,
            data={"chat_id": str(user.telegram_chat_id)},
            files={"photo": (filename, data, "image/png")},
            timeout=30.0,
        )
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise EntryShareError(
            f"Failed to send share image to Telegram: {exc}",
            code=ErrorCode.TELEGRAM_SEND_FAILED,
            status_code=502,
        ) from exc

    if not isinstance(payload, dict) or not payload.get("ok"):
        # Typically 403 "bot was blocked by the user" or a chat that never started the bot.
        raise EntryShareError(
            f"Telegram API rejected sendPhoto: {payload}",
            code=ErrorCode.TELEGRAM_SEND_REJECTED,
            status_code=502,
        )
