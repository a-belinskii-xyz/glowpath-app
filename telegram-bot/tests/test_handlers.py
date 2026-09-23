from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from bot.handlers import handle_update


def test_log_opens_mini_app_create(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    with patch("bot.handlers.send_message", new_callable=AsyncMock) as send:
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/log",
                    }
                }
            )
        )
        send.assert_awaited_once()
        kwargs = send.await_args.kwargs
        assert kwargs["text"] == "Log your mood in GlowPath."
        button = kwargs["reply_markup"]["inline_keyboard"][0][0]
        assert button["text"] == "Log mood"
        assert button["web_app"] == {"url": "https://app.example?tgWebAppStartParam=create"}


def test_start_log_opens_daily_create(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    with patch("bot.handlers.send_message", new_callable=AsyncMock) as send:
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/start log",
                    }
                }
            )
        )
        send.assert_awaited_once()
        button = send.await_args.kwargs["reply_markup"]["inline_keyboard"][0][0]
        assert button["web_app"]["url"].endswith("tgWebAppStartParam=create_daily")


def test_legacy_wizard_callback_is_retired() -> None:
    with patch("bot.handlers.answer_callback_query", new_callable=AsyncMock) as answer:
        asyncio.run(
            handle_update(
                {
                    "callback_query": {
                        "id": "cb1",
                        "from": {"id": 2, "language_code": "en"},
                        "data": "w:score:4",
                        "message": {"chat": {"id": 1}, "message_id": 9},
                    }
                }
            )
        )
        answer.assert_awaited_once()
        assert answer.await_args.kwargs["show_alert"] is True
        assert "app" in answer.await_args.kwargs["text"].lower()


def test_start_new_user_opens_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(return_value={"linked": False})
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/start",
                    }
                }
            )
        )
        send.assert_awaited_once()
        kwargs = send.await_args.kwargs
        assert "website" in kwargs["text"].lower()
        rows = kwargs["reply_markup"]["inline_keyboard"]
        assert len(rows) == 1
        button = rows[0][0]
        assert button["text"] == "Open App"
        assert button["web_app"] == {
            "url": "https://app.example?tgWebAppStartParam=onboarding"
        }


def test_start_incomplete_onboarding_continues_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(
        return_value={"linked": True, "onboarding_completed": False, "locale": "en"}
    )
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/start",
                    }
                }
            )
        )
        kwargs = send.await_args.kwargs
        assert "finish setup" in kwargs["text"].lower()
        button = kwargs["reply_markup"]["inline_keyboard"][0][0]
        assert button["web_app"]["url"].endswith("tgWebAppStartParam=onboarding")


def test_start_onboarded_user_gets_home_keyboard(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://app.example")
    me = AsyncMock(
        return_value={"linked": True, "onboarding_completed": True, "locale": "ru"}
    )
    with (
        patch("bot.handlers.api_client.me", me),
        patch("bot.handlers.send_message", new_callable=AsyncMock) as send,
    ):
        asyncio.run(
            handle_update(
                {
                    "message": {
                        "chat": {"id": 1},
                        "from": {"id": 2, "language_code": "en"},
                        "text": "/start",
                    }
                }
            )
        )
        rows = send.await_args.kwargs["reply_markup"]["inline_keyboard"]
        assert rows[0][0]["text"] == "Записать настроение"
        assert rows[0][0]["web_app"]["url"].endswith("tgWebAppStartParam=create")
        assert rows[1][0]["text"] == "Открыть приложение"
        assert rows[1][0]["web_app"] == {"url": "https://app.example"}
