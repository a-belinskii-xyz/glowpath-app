from __future__ import annotations

import logging
from typing import Any

from bot.api_client import ApiClientError, api_client
from bot.config import settings
from bot.i18n import normalize_bot_locale, t
from bot.keyboards import (
    START_CREATE,
    START_CREATE_DAILY,
    START_ONBOARDING,
    linked_home_keyboard,
    mini_app_keyboard,
)
from bot.telegram_api import answer_callback_query, send_message

logger = logging.getLogger(__name__)


async def handle_update(update: dict[str, Any]) -> None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        await _handle_callback(callback)
        return

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")
    if not isinstance(chat_id, int) or not isinstance(telegram_user_id, int):
        return

    locale = _locale_from_user(from_user)
    text = message.get("text")
    if not isinstance(text, str):
        return

    command, payload = _parse_command(text)
    if command == "/start":
        await _handle_start(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            payload=payload,
        )
        return
    if command == "/unlink":
        await _handle_unlink(chat_id=chat_id, telegram_user_id=telegram_user_id, locale=locale)
        return
    if command == "/help":
        await send_app_message(chat_id=chat_id, locale=locale, text=t(locale, "help"))
        return
    if command == "/log":
        await _open_log(
            chat_id=chat_id,
            locale=locale,
            start=START_CREATE,
        )
        return
    if command == "/cancel":
        await send_app_message(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "wizard_retired"),
        )


async def _handle_callback(callback: dict[str, Any]) -> None:
    callback_id = callback.get("id")
    from_user = callback.get("from") or {}
    locale = _locale_from_user(from_user)
    if not isinstance(callback_id, str):
        return
    await answer_callback_query(
        callback_query_id=callback_id,
        text=t(locale, "wizard_retired"),
        show_alert=True,
    )


def _mini_app_url() -> str | None:
    url = settings.telegram_mini_app_url.strip()
    return url or None


def _home_markup(locale: str | None) -> dict[str, Any] | None:
    url = _mini_app_url()
    if not url:
        return None
    return linked_home_keyboard(locale=locale, url=url)


def _log_markup(locale: str | None, *, start: str) -> dict[str, Any] | None:
    url = _mini_app_url()
    if not url:
        return None
    return mini_app_keyboard(locale=locale, url=url, start=start, button_key="log_mood")


def _onboarding_markup(locale: str | None) -> dict[str, Any] | None:
    url = _mini_app_url()
    if not url:
        return None
    return mini_app_keyboard(
        locale=locale,
        url=url,
        start=START_ONBOARDING,
        button_key="open_app",
    )


async def send_app_message(
    *,
    chat_id: int,
    locale: str | None,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    markup = reply_markup
    if markup is None:
        markup = _home_markup(locale)
    await send_message(chat_id=chat_id, text=text, reply_markup=markup)


async def _open_onboarding(*, chat_id: int, locale: str | None, text: str) -> None:
    markup = _onboarding_markup(locale)
    if markup is None:
        await send_message(chat_id=chat_id, text=t(locale, "mini_app_not_configured"))
        return
    await send_message(chat_id=chat_id, text=text, reply_markup=markup)


async def _open_log(*, chat_id: int, locale: str | None, start: str) -> None:
    markup = _log_markup(locale, start=start)
    if markup is None:
        await send_app_message(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "mini_app_not_configured"),
        )
        return
    await send_app_message(
        chat_id=chat_id,
        locale=locale,
        text=t(locale, "log_prompt"),
        reply_markup=markup,
    )


async def _handle_start(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    payload: str | None,
) -> None:
    if payload in {"log", "create", START_CREATE_DAILY}:
        start = START_CREATE_DAILY if payload in {"log", START_CREATE_DAILY} else START_CREATE
        await _open_log(chat_id=chat_id, locale=locale, start=start)
        return

    if payload == START_ONBOARDING:
        await _open_onboarding(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "welcome"),
        )
        return

    if not payload:
        try:
            me = await api_client.me(telegram_user_id=telegram_user_id)
        except ApiClientError as exc:
            logger.warning("me failed: %s", exc.message)
            await _open_onboarding(
                chat_id=chat_id,
                locale=locale,
                text=t(locale, "welcome"),
            )
            return
        if me.get("linked") and me.get("onboarding_completed"):
            linked_locale = normalize_bot_locale(me.get("locale") or locale)
            await send_app_message(
                chat_id=chat_id,
                locale=linked_locale,
                text=t(linked_locale, "already_linked"),
            )
            return
        if me.get("linked"):
            linked_locale = normalize_bot_locale(me.get("locale") or locale)
            await _open_onboarding(
                chat_id=chat_id,
                locale=linked_locale,
                text=t(linked_locale, "continue_onboarding"),
            )
            return
        await _open_onboarding(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "welcome"),
        )
        return

    try:
        me = await api_client.link(
            code=payload,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=chat_id,
            locale=locale,
        )
    except ApiClientError as exc:
        await send_message(
            chat_id=chat_id,
            text=t(locale, "link_failed", detail=exc.message),
        )
        return

    linked_locale = normalize_bot_locale(me.get("locale") or locale)
    if me.get("onboarding_completed"):
        await send_app_message(
            chat_id=chat_id,
            locale=linked_locale,
            text=t(linked_locale, "linked_ok"),
        )
        return
    await _open_onboarding(
        chat_id=chat_id,
        locale=linked_locale,
        text=t(linked_locale, "linked_ok"),
    )


async def _handle_unlink(*, chat_id: int, telegram_user_id: int, locale: str | None) -> None:
    try:
        await api_client.unlink(telegram_user_id=telegram_user_id)
    except ApiClientError as exc:
        await send_message(
            chat_id=chat_id,
            text=t(locale, "unlink_failed", detail=exc.message),
        )
        return
    await send_message(chat_id=chat_id, text=t(locale, "unlinked_ok"))


def _locale_from_user(from_user: dict[str, Any]) -> str | None:
    locale = from_user.get("language_code")
    return locale if isinstance(locale, str) else None


def _parse_command(text: str) -> tuple[str | None, str | None]:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return None, None
    command = parts[0].split("@", 1)[0].lower()
    if not command.startswith("/"):
        return None, None
    payload = parts[1].strip() if len(parts) > 1 else None
    return command, payload or None
