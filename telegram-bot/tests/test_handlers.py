from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from bot.handlers import handle_update

PROMPT = {
    "text": "How are you right now?",
    "reply_markup": {
        "inline_keyboard": [[{"text": "🙂", "callback_data": "q:4"}]],
    },
}
ONBOARDED = {"linked": True, "onboarding_completed": True, "locale": "en"}


def _message_update(text: str, *, language_code: str = "en") -> dict:
    return {
        "message": {
            "chat": {"id": 1},
            "from": {"id": 2, "language_code": language_code},
            "text": text,
        }
    }


def _callback_update(data: str, *, message_text: str | None = "How are you?") -> dict:
    message: dict = {"chat": {"id": 1}, "message_id": 9}
    if message_text is not None:
        message["text"] = message_text
    return {
        "callback_query": {
            "id": "cb1",
            "from": {"id": 2, "language_code": "en"},
            "data": data,
            "message": message,
        }
    }


def test_log_sends_mood_buttons_from_api() -> None:
    with (
        patch("bot.handlers.api_client.me", AsyncMock(return_value=ONBOARDED)),
        patch("bot.handlers.api_client.quick_log_prompt", AsyncMock(return_value=PROMPT)) as prompt,
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/log")))
    prompt.assert_awaited_once_with(telegram_user_id=2)
    send.assert_awaited_once_with(
        chat_id=1, text=PROMPT["text"], reply_markup=PROMPT["reply_markup"]
    )


def test_log_sends_new_user_to_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    with (
        patch("bot.handlers.api_client.me", AsyncMock(return_value={"linked": False})),
        patch("bot.handlers.api_client.quick_log_prompt", new_callable=AsyncMock) as prompt,
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/log")))
    prompt.assert_not_awaited()
    button = send.await_args.kwargs["reply_markup"]["inline_keyboard"][0][0]
    assert button["web_app"]["url"].endswith("tgWebAppStartParam=onboarding")


def test_log_falls_back_to_mini_app_when_api_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.api_client import ApiClientError
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    with (
        patch("bot.handlers.api_client.me", AsyncMock(return_value=ONBOARDED)),
        patch(
            "bot.handlers.api_client.quick_log_prompt",
            AsyncMock(side_effect=ApiClientError("down", status_code=502)),
        ),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/log")))
    kwargs = send.await_args.kwargs
    assert kwargs["text"] == "Log your mood in GlowPath."
    button = kwargs["reply_markup"]["inline_keyboard"][0][0]
    assert button["web_app"] == {"url": "https://app.example?tgWebAppStartParam=create"}


def test_start_log_sends_mood_buttons() -> None:
    with (
        patch("bot.handlers.api_client.me", AsyncMock(return_value=ONBOARDED)),
        patch("bot.handlers.api_client.quick_log_prompt", AsyncMock(return_value=PROMPT)),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/start log")))
    assert send.await_args.kwargs["reply_markup"] == PROMPT["reply_markup"]


def test_quick_tap_is_relayed_and_message_edited() -> None:
    reply = {
        "text": "How are you?\n\n✓ Logged: 🙂 good · 21:40",
        "reply_markup": {"inline_keyboard": [[{"text": "•🙂•", "callback_data": "q:4"}]]},
        "toast": "Logged",
        "alert": False,
    }
    with (
        patch("bot.handlers.api_client.quick_log_tap", AsyncMock(return_value=reply)) as tap,
        patch("bot.handlers.answer_callback_query", new_callable=AsyncMock) as answer,
        patch("bot.handlers.edit_message_text", new_callable=AsyncMock) as edit,
    ):
        asyncio.run(handle_update(_callback_update("q:4:tok")))
    tap.assert_awaited_once_with(
        telegram_user_id=2,
        chat_id=1,
        message_id=9,
        data="q:4:tok",
        message_text="How are you?",
        locale="en",
    )
    answer.assert_awaited_once_with(callback_query_id="cb1", text="Logged", show_alert=False)
    edit.assert_awaited_once_with(
        chat_id=1, message_id=9, text=reply["text"], reply_markup=reply["reply_markup"]
    )


def test_quick_tap_without_text_only_answers() -> None:
    reply = {"text": None, "reply_markup": None, "toast": "No longer works", "alert": True}
    with (
        patch("bot.handlers.api_client.quick_log_tap", AsyncMock(return_value=reply)) as tap,
        patch("bot.handlers.answer_callback_query", new_callable=AsyncMock) as answer,
        patch("bot.handlers.edit_message_text", new_callable=AsyncMock) as edit,
    ):
        asyncio.run(handle_update(_callback_update("q:9", message_text=None)))
    assert tap.await_args.kwargs["message_text"] is None
    answer.assert_awaited_once_with(
        callback_query_id="cb1", text="No longer works", show_alert=True
    )
    edit.assert_not_awaited()


def test_quick_tap_api_error_shows_alert() -> None:
    from bot.api_client import ApiClientError

    with (
        patch(
            "bot.handlers.api_client.quick_log_tap",
            AsyncMock(side_effect=ApiClientError("down", status_code=502)),
        ),
        patch("bot.handlers.answer_callback_query", new_callable=AsyncMock) as answer,
        patch("bot.handlers.edit_message_text", new_callable=AsyncMock) as edit,
    ):
        asyncio.run(handle_update(_callback_update("q:4")))
    assert answer.await_args.kwargs["show_alert"] is True
    assert "try again" in answer.await_args.kwargs["text"].lower()
    edit.assert_not_awaited()


def test_legacy_wizard_callback_is_retired() -> None:
    with (
        patch("bot.handlers.api_client.quick_log_tap", new_callable=AsyncMock) as tap,
        patch("bot.handlers.answer_callback_query", new_callable=AsyncMock) as answer,
    ):
        asyncio.run(handle_update(_callback_update("w:score:4")))
    tap.assert_not_awaited()
    answer.assert_awaited_once()
    assert answer.await_args.kwargs["show_alert"] is True
    assert "/log" in answer.await_args.kwargs["text"]


def test_start_new_user_opens_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(return_value={"linked": False})
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/start")))
        send.assert_awaited_once()
        kwargs = send.await_args.kwargs
        assert "website" in kwargs["text"].lower()
        rows = kwargs["reply_markup"]["inline_keyboard"]
        assert len(rows) == 1
        button = rows[0][0]
        assert button["text"] == "Open App"
        assert button["web_app"] == {"url": "https://app.example?tgWebAppStartParam=onboarding"}


def test_start_incomplete_onboarding_continues_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(return_value={"linked": True, "onboarding_completed": False, "locale": "en"})
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/start")))
        kwargs = send.await_args.kwargs
        assert "finish setup" in kwargs["text"].lower()
        button = kwargs["reply_markup"]["inline_keyboard"][0][0]
        assert button["web_app"]["url"].endswith("tgWebAppStartParam=onboarding")


def test_start_onboarded_user_gets_mood_buttons() -> None:
    me = AsyncMock(return_value=ONBOARDED)
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.api_client.quick_log_prompt", AsyncMock(return_value=PROMPT)),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_message_update("/start")))
    me.assert_awaited_once()
    send.assert_awaited_once_with(
        chat_id=1, text=PROMPT["text"], reply_markup=PROMPT["reply_markup"]
    )


def _start_update(text: str) -> dict:
    return {
        "message": {
            "chat": {"id": 1},
            "from": {"id": 2, "language_code": "ru"},
            "text": text,
        }
    }


def test_start_login_confirms_website_sign_in() -> None:
    with (
        patch("bot.handlers.api_client.confirm_login", new_callable=AsyncMock) as confirm,
        patch("bot.handlers.api_client.link", new_callable=AsyncMock) as link,
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_start_update("/start login_abcdefgh123")))
    confirm.assert_awaited_once_with(code="abcdefgh123", telegram_user_id=2, locale="ru")
    link.assert_not_awaited()
    assert "Вход подтверждён" in send.await_args.kwargs["text"]


def test_start_login_reports_expired_link() -> None:
    from bot.api_client import ApiClientError

    with (
        patch(
            "bot.handlers.api_client.confirm_login",
            new_callable=AsyncMock,
            side_effect=ApiClientError("expired", status_code=400),
        ),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(handle_update(_start_update("/start login_abcdefgh123")))
    assert "устарела" in send.await_args.kwargs["text"]


def test_start_with_source_label_passes_it_to_mini_app(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(return_value={"linked": False})
    link = AsyncMock()
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.api_client.link", link),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/start src_tiktok",
                    }
                }
            )
        )
        link.assert_not_awaited()
        button = send.await_args.kwargs["reply_markup"]["inline_keyboard"][0][0]
        assert button["web_app"] == {"url": "https://app.example?tgWebAppStartParam=src_tiktok"}
