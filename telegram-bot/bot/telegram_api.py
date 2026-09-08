from __future__ import annotations

import logging
from typing import Any

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


def _bot_url(method: str) -> str:
    return f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/{method}"


async def set_webhook() -> None:
    """Register the public webhook URL with Telegram when configured."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty — skipping setWebhook")
        return
    if not settings.telegram_webhook_url:
        logger.info("TELEGRAM_WEBHOOK_URL is empty — skipping setWebhook")
        return

    payload: dict[str, Any] = {
        "url": settings.telegram_webhook_url.rstrip("/") + settings.telegram_webhook_path,
        "drop_pending_updates": False,
    }
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_bot_url("setWebhook"), json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"setWebhook failed: {data}")
        logger.info("Telegram webhook registered: %s", payload["url"])


BOT_COMMANDS = {
    "": [
        {"command": "start", "description": "Open GlowPath"},
        {"command": "log", "description": "Log your mood"},
        {"command": "help", "description": "How to use the bot"},
        {"command": "unlink", "description": "Disconnect Telegram"},
    ],
    "ru": [
        {"command": "start", "description": "Открыть GlowPath"},
        {"command": "log", "description": "Записать настроение"},
        {"command": "help", "description": "Как пользоваться ботом"},
        {"command": "unlink", "description": "Отвязать Telegram"},
    ],
}


async def set_my_commands() -> None:
    if not settings.telegram_bot_token:
        return
    async with httpx.AsyncClient(timeout=30.0) as client:
        for language_code, commands in BOT_COMMANDS.items():
            payload: dict[str, Any] = {"commands": commands}
            if language_code:
                payload["language_code"] = language_code
            response = await client.post(_bot_url("setMyCommands"), json=payload)
            if response.status_code >= 400:
                logger.error(
                    "setMyCommands failed language=%s status=%s body=%s",
                    language_code or "default",
                    response.status_code,
                    response.text,
                )
                continue
            data = response.json()
            if not data.get("ok"):
                logger.error(
                    "setMyCommands rejected language=%s: %s",
                    language_code or "default",
                    data,
                )
                continue
        logger.info("Telegram bot commands registered")


async def delete_webhook() -> None:
    if not settings.telegram_bot_token:
        return
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(_bot_url("deleteWebhook"), json={"drop_pending_updates": False})


async def send_message(
    *,
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    if not settings.telegram_bot_token:
        logger.warning("Cannot sendMessage: bot token is empty")
        return
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_bot_url("sendMessage"), json=payload)
        if response.status_code >= 400:
            logger.error(
                "sendMessage failed status=%s body=%s",
                response.status_code,
                response.text,
            )


async def answer_callback_query(
    *,
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool = False,
) -> None:
    if not settings.telegram_bot_token:
        return
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(_bot_url("answerCallbackQuery"), json=payload)
        if response.status_code >= 400:
            logger.error(
                "answerCallbackQuery failed status=%s body=%s",
                response.status_code,
                response.text,
            )


async def edit_message_reply_markup(
    *,
    chat_id: int,
    message_id: int,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    if not settings.telegram_bot_token:
        return
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(_bot_url("editMessageReplyMarkup"), json=payload)
        if response.status_code >= 400:
            logger.debug(
                "editMessageReplyMarkup failed status=%s body=%s",
                response.status_code,
                response.text,
            )


async def get_file(file_id: str) -> dict[str, Any]:
    if not settings.telegram_bot_token:
        raise RuntimeError("Bot token is empty")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_bot_url("getFile"), json={"file_id": file_id})
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"getFile failed: {data}")
        result = data.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("getFile returned unexpected payload")
        return result


async def download_file(file_path: str) -> bytes:
    if not settings.telegram_bot_token:
        raise RuntimeError("Bot token is empty")
    url = f"{TELEGRAM_API}/file/bot{settings.telegram_bot_token}/{file_path}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
