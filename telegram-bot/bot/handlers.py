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
from bot.telegram_api import answer_callback_query, edit_message_text, send_message

logger = logging.getLogger(__name__)

# Website sign-in: /start login_<code> (see telegram_bot_login_service in the API).
LOGIN_START_PREFIX = "login_"
# Marketing links: /start src_<label>; the label rides into the Mini App as its start param.
SIGNUP_SOURCE_PREFIX = "src_"
# Mood buttons the API writes into reminders and /log messages. The bot only relays a
# tap on them; their format lives in the API (app/core/telegram_quick_log.py).
QUICK_LOG_CALLBACK_PREFIX = "q:"


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
        await _send_quick_log(chat_id=chat_id, telegram_user_id=telegram_user_id, locale=locale)
        return
    if command == "/cancel":
        await send_app_message(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "nothing_to_cancel"),
        )


async def _handle_callback(callback: dict[str, Any]) -> None:
    callback_id = callback.get("id")
    from_user = callback.get("from") or {}
    locale = _locale_from_user(from_user)
    if not isinstance(callback_id, str):
        return
    data = callback.get("data")
    message = callback.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")
    telegram_user_id = from_user.get("id")
    if (
        isinstance(data, str)
        and data.startswith(QUICK_LOG_CALLBACK_PREFIX)
        and isinstance(chat_id, int)
        and isinstance(message_id, int)
        and isinstance(telegram_user_id, int)
    ):
        text = message.get("text")
        await _handle_quick_tap(
            callback_id=callback_id,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            data=data,
            message_text=text if isinstance(text, str) else None,
            locale=locale,
        )
        return
    # Buttons of the chat wizard (retired 08.09) still sit in old messages.
    await answer_callback_query(
        callback_query_id=callback_id,
        text=t(locale, "button_stale"),
        show_alert=True,
    )


async def _handle_quick_tap(
    *,
    callback_id: str,
    telegram_user_id: int,
    chat_id: int,
    message_id: int,
    data: str,
    message_text: str | None,
    locale: str | None,
) -> None:
    try:
        reply = await api_client.quick_log_tap(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            data=data,
            message_text=message_text,
            locale=locale,
        )
    except ApiClientError as exc:
        logger.warning("quick log tap failed: %s", exc.message)
        await answer_callback_query(
            callback_query_id=callback_id,
            text=t(locale, "quick_log_failed"),
            show_alert=True,
        )
        return
    toast = reply.get("toast")
    await answer_callback_query(
        callback_query_id=callback_id,
        text=toast if isinstance(toast, str) else None,
        show_alert=bool(reply.get("alert")),
    )
    text = reply.get("text")
    if not isinstance(text, str) or not text:
        return
    markup = reply.get("reply_markup")
    await edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=markup if isinstance(markup, dict) else None,
    )


async def _send_quick_log(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    me: dict[str, Any] | None = None,
) -> None:
    """Ask "How are you?" with mood buttons, or send newcomers to set up the app first."""
    if me is None:
        try:
            me = await api_client.me(telegram_user_id=telegram_user_id)
        except ApiClientError as exc:
            logger.warning("me failed: %s", exc.message)
            await _open_log(chat_id=chat_id, locale=locale, start=START_CREATE)
            return
    if not me.get("linked"):
        await _open_onboarding(chat_id=chat_id, locale=locale, text=t(locale, "welcome"))
        return
    linked_locale = normalize_bot_locale(me.get("locale") or locale)
    if not me.get("onboarding_completed"):
        await _open_onboarding(
            chat_id=chat_id,
            locale=linked_locale,
            text=t(linked_locale, "continue_onboarding"),
        )
        return
    try:
        prompt = await api_client.quick_log_prompt(telegram_user_id=telegram_user_id)
    except ApiClientError as exc:
        logger.warning("quick log prompt failed: %s", exc.message)
        await _open_log(chat_id=chat_id, locale=linked_locale, start=START_CREATE)
        return
    text = prompt.get("text")
    markup = prompt.get("reply_markup")
    if not isinstance(text, str) or not isinstance(markup, dict):
        await _open_log(chat_id=chat_id, locale=linked_locale, start=START_CREATE)
        return
    await send_message(chat_id=chat_id, text=text, reply_markup=markup)


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


def _onboarding_markup(locale: str | None, *, start: str) -> dict[str, Any] | None:
    url = _mini_app_url()
    if not url:
        return None
    return mini_app_keyboard(
        locale=locale,
        url=url,
        start=start,
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


async def _open_onboarding(
    *,
    chat_id: int,
    locale: str | None,
    text: str,
    start: str = START_ONBOARDING,
) -> None:
    markup = _onboarding_markup(locale, start=start)
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
        await _send_quick_log(chat_id=chat_id, telegram_user_id=telegram_user_id, locale=locale)
        return

    if payload and payload.startswith(LOGIN_START_PREFIX):
        await _confirm_login(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            locale=locale,
            code=payload.removeprefix(LOGIN_START_PREFIX),
        )
        return

    # A new user from a labelled link opens the Mini App with that label, so the
    # account records where it came from; the app sends new users to onboarding anyway.
    onboarding_start = START_ONBOARDING
    if payload and payload.startswith(SIGNUP_SOURCE_PREFIX):
        onboarding_start = payload
        payload = None

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
                start=onboarding_start,
            )
            return
        if me.get("linked") and me.get("onboarding_completed"):
            await _send_quick_log(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                locale=locale,
                me=me,
            )
            return
        if me.get("linked"):
            linked_locale = normalize_bot_locale(me.get("locale") or locale)
            await _open_onboarding(
                chat_id=chat_id,
                locale=linked_locale,
                text=t(linked_locale, "continue_onboarding"),
                start=onboarding_start,
            )
            return
        await _open_onboarding(
            chat_id=chat_id,
            locale=locale,
            text=t(locale, "welcome"),
            start=onboarding_start,
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


async def _confirm_login(
    *,
    chat_id: int,
    telegram_user_id: int,
    locale: str | None,
    code: str,
) -> None:
    try:
        await api_client.confirm_login(code=code, telegram_user_id=telegram_user_id, locale=locale)
    except ApiClientError as exc:
        logger.info("login confirm failed: %s", exc.message)
        await send_message(chat_id=chat_id, text=t(locale, "login_failed"))
        return
    await send_message(chat_id=chat_id, text=t(locale, "login_ok"))


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
