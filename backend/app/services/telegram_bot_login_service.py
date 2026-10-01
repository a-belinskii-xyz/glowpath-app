"""Website sign-in through the bot: the site opens ``t.me/<bot>?start=login_<code>``,
the bot confirms the code for the Telegram account that pressed Start, and the site
polls with its own secret until tokens are ready."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.i18n import normalize_locale
from app.core.security import hash_token
from app.core.timezones import normalize_timezone
from app.models.telegram_login_request import TelegramLoginRequest
from app.services.auth_service import AuthError, TokenPair
from app.services.telegram_auth_service import login_or_create_telegram_user
from app.services.telegram_link_service import bot_is_configured

LOGIN_START_PREFIX = "login_"


@dataclass(frozen=True, slots=True)
class BotLoginStart:
    poll_token: str
    deep_link: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class BotLoginPoll:
    status: Literal["pending", "confirmed", "expired"]
    tokens: TokenPair | None = None


def start_bot_login(
    db: Session,
    *,
    timezone: str,
    visitor_id: uuid.UUID | None = None,
) -> BotLoginStart:
    if not bot_is_configured():
        raise AuthError(
            "Telegram bot is not configured",
            code=ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED,
            status_code=503,
        )
    try:
        timezone_name = normalize_timezone(timezone)
    except ValueError as exc:
        raise AuthError(str(exc), code=ErrorCode.INVALID_TIMEZONE, status_code=400) from exc

    code = secrets.token_urlsafe(16)
    poll_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.telegram_link_code_expire_minutes)
    db.add(
        TelegramLoginRequest(
            code_hash=hash_token(code),
            poll_hash=hash_token(poll_token),
            timezone=timezone_name,
            visitor_id=visitor_id,
            expires_at=expires_at,
        )
    )
    db.commit()
    username = settings.telegram_bot_username.strip()
    deep_link = f"https://t.me/{username}?start={LOGIN_START_PREFIX}{code}"
    return BotLoginStart(poll_token=poll_token, deep_link=deep_link, expires_at=expires_at)


def confirm_bot_login(
    db: Session,
    *,
    code: str,
    telegram_user_id: int,
    locale: str | None,
) -> None:
    row = db.scalar(
        select(TelegramLoginRequest).where(TelegramLoginRequest.code_hash == hash_token(code))
    )
    if row is None or row.confirmed_at is not None:
        raise AuthError(
            "Sign-in link is invalid or already used",
            code=ErrorCode.TELEGRAM_LINK_CODE_INVALID,
            status_code=400,
        )
    if row.expires_at <= datetime.now(UTC):
        raise AuthError(
            "Sign-in link has expired",
            code=ErrorCode.TELEGRAM_LINK_CODE_EXPIRED,
            status_code=400,
        )
    row.telegram_user_id = telegram_user_id
    row.telegram_locale = normalize_locale(locale) if locale else None
    row.confirmed_at = datetime.now(UTC)
    db.commit()


def poll_bot_login(db: Session, *, poll_token: str) -> BotLoginPoll:
    row = db.scalar(
        select(TelegramLoginRequest)
        .where(TelegramLoginRequest.poll_hash == hash_token(poll_token))
        .with_for_update()
    )
    if row is None or row.consumed_at is not None:
        return BotLoginPoll(status="expired")
    if row.confirmed_at is None or row.telegram_user_id is None:
        if row.expires_at <= datetime.now(UTC):
            return BotLoginPoll(status="expired")
        return BotLoginPoll(status="pending")

    row.consumed_at = datetime.now(UTC)
    tokens = login_or_create_telegram_user(
        db,
        telegram_user_id=row.telegram_user_id,
        timezone=row.timezone,
        locale=row.telegram_locale,
        visitor_id=row.visitor_id,
    )
    return BotLoginPoll(status="confirmed", tokens=tokens)
