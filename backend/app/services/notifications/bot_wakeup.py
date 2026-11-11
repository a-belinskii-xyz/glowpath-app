"""Wake the Telegram bot service before reminders with buttons go out.

A tap on a reminder button goes to the bot's webhook. On Render free the bot sleeps
after ~15 minutes without traffic, so the first tap after a quiet spell would wait for
a cold start. A pass that is about to send Telegram reminders pings the bot first
(``TELEGRAM_BOT_HEALTH_URL``), in the background, so sending is never held up.
"""

from __future__ import annotations

import logging
import threading

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Long enough to outlast a cold start; the ping runs in its own thread.
_PING_TIMEOUT_SECONDS = 60.0


def wake_telegram_bot() -> threading.Thread | None:
    """Start a background GET to the bot's health URL. Returns the thread, if any."""
    url = settings.telegram_bot_health_url.strip()
    if not url:
        return None
    thread = threading.Thread(
        target=_ping,
        args=(url,),
        name="wake-telegram-bot",
        daemon=True,
    )
    thread.start()
    return thread


def _ping(url: str) -> None:
    try:
        httpx.get(url, timeout=_PING_TIMEOUT_SECONDS)
    except Exception as exc:  # best effort: a failed ping must never affect reminders
        logger.info("could not wake the Telegram bot: %s", exc)
