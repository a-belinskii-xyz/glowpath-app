"""Deliver a client-rendered entry share image to the user's Telegram chat.

The Mini App cannot always hand a file to the phone's share sheet, so the bot
sends the picture into the user's chat instead; from there it can be forwarded
or saved to the gallery.
"""

from __future__ import annotations

from app.core.error_codes import ErrorCode
from app.models.user import User
from app.services.telegram_delivery import TelegramDeliveryError, send_to_user_chat

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Telegram's sendPhoto accepts photos up to 10 MB.
SHARE_IMAGE_MAX_BYTES = 10 * 1024 * 1024


class EntryShareError(TelegramDeliveryError):
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
    send_to_user_chat(
        user=user,
        method="sendPhoto",
        field="photo",
        filename=filename,
        data=data,
        content_type="image/png",
    )
