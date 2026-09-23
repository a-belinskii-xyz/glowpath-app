"""Validate Telegram Mini App initData (HMAC-SHA256).

See https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl

from app.core.error_codes import ErrorCode
from app.core.errors import AppError


class TelegramInitDataError(AppError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramWebAppUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool = False


@dataclass(frozen=True, slots=True)
class TelegramInitData:
    user: TelegramWebAppUser
    auth_date: datetime
    start_param: str | None = None
    query_id: str | None = None


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> TelegramInitData:
    raw = init_data.strip()
    if not raw or not bot_token.strip():
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )

    pairs = dict(parse_qsl(raw, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )

    auth_date_raw = pairs.get("auth_date", "")
    try:
        auth_unix = int(auth_date_raw)
    except ValueError as exc:
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        ) from exc

    auth_date = datetime.fromtimestamp(auth_unix, tz=UTC)
    moment = now or datetime.now(UTC)
    age = (moment - auth_date).total_seconds()
    if age < -30 or age > max_age_seconds:
        raise TelegramInitDataError(
            "Telegram authentication data has expired",
            code=ErrorCode.TELEGRAM_INIT_DATA_EXPIRED,
            status_code=401,
        )

    user = _parse_user(pairs.get("user"))
    start_param = pairs.get("start_param") or None
    query_id = pairs.get("query_id") or None
    return TelegramInitData(
        user=user,
        auth_date=auth_date,
        start_param=start_param,
        query_id=query_id,
    )


def _parse_user(raw: str | None) -> TelegramWebAppUser:
    if not raw:
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        ) from exc
    if not isinstance(payload, dict):
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )

    user_id = payload.get("id")
    first_name = payload.get("first_name")
    if not isinstance(user_id, int) or user_id <= 0 or not isinstance(first_name, str):
        raise TelegramInitDataError(
            "Invalid Telegram authentication data",
            code=ErrorCode.INVALID_TELEGRAM_INIT_DATA,
            status_code=401,
        )

    return TelegramWebAppUser(
        id=user_id,
        first_name=first_name,
        last_name=_optional_str(payload.get("last_name")),
        username=_optional_str(payload.get("username")),
        language_code=_optional_str(payload.get("language_code")),
        is_premium=bool(payload.get("is_premium")),
    )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
