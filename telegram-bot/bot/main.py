from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status

from bot.config import settings
from bot.handlers import handle_update
from bot.telegram_api import set_webhook

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        await set_webhook()
    except Exception:
        logger.exception("Failed to register Telegram webhook on startup")
    yield


app = FastAPI(
    title="GlowPath Telegram Bot",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    configured = "yes" if settings.telegram_bot_token else "no"
    return {"status": "ok", "bot_token_configured": configured}


@app.post(settings.telegram_webhook_path)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """Receive Telegram updates and dispatch to command handlers."""
    if (
        settings.telegram_webhook_secret
        and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot token is not configured",
        )

    update: dict[str, Any] = await request.json()
    logger.info("Received Telegram update_id=%s", update.get("update_id"))
    try:
        await handle_update(update)
    except Exception:
        logger.exception("Failed to handle Telegram update")
    return {"ok": True}
