from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bot.i18n import t

START_CREATE = "create"
START_CREATE_DAILY = "create_daily"
START_GOALS = "goals"


def inline_keyboard(rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


def with_start_param(url: str, start: str | None) -> str:
    if not start:
        return url
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["tgWebAppStartParam"] = start
    return urlunparse(parts._replace(query=urlencode(query)))


def mini_app_keyboard(
    *,
    locale: str | None,
    url: str,
    start: str | None = None,
    button_key: str = "open_app",
) -> dict[str, Any]:
    return inline_keyboard(
        [
            [
                {
                    "text": t(locale, button_key),
                    "web_app": {"url": with_start_param(url, start)},
                }
            ]
        ]
    )


def linked_home_keyboard(*, locale: str | None, url: str) -> dict[str, Any]:
    return inline_keyboard(
        [
            [
                {
                    "text": t(locale, "log_mood"),
                    "web_app": {"url": with_start_param(url, START_CREATE)},
                }
            ],
            [
                {
                    "text": t(locale, "open_app"),
                    "web_app": {"url": url},
                }
            ],
        ]
    )
