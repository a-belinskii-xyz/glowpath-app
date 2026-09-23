from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
from app.core.error_codes import ErrorCode
from app.core.telegram_init_data import TelegramInitDataError, validate_init_data

BOT_TOKEN = "test-bot-token:ABC"


def build_init_data(
    *,
    user: dict[str, object],
    bot_token: str = BOT_TOKEN,
    auth_date: int | None = None,
    extra: dict[str, str] | None = None,
    hash_override: str | None = None,
) -> str:
    auth_ts = auth_date if auth_date is not None else int(datetime.now(UTC).timestamp())
    fields: dict[str, str] = {
        "auth_date": str(auth_ts),
        "user": json.dumps(user, separators=(",", ":")),
    }
    if extra:
        fields.update(extra)
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = hash_override if hash_override is not None else digest
    return urlencode(fields)


def test_validate_init_data_accepts_signed_payload() -> None:
    init_data = build_init_data(
        user={"id": 4242, "first_name": "Ada", "language_code": "ru"},
        extra={"start_param": "create"},
    )
    parsed = validate_init_data(init_data, BOT_TOKEN, max_age_seconds=3600)
    assert parsed.user.id == 4242
    assert parsed.user.first_name == "Ada"
    assert parsed.user.language_code == "ru"
    assert parsed.start_param == "create"


def test_validate_init_data_rejects_bad_hash() -> None:
    init_data = build_init_data(
        user={"id": 1, "first_name": "Ada"},
        hash_override="0" * 64,
    )
    with pytest.raises(TelegramInitDataError) as exc:
        validate_init_data(init_data, BOT_TOKEN, max_age_seconds=3600)
    assert exc.value.code == ErrorCode.INVALID_TELEGRAM_INIT_DATA


def test_validate_init_data_rejects_expired_payload() -> None:
    init_data = build_init_data(
        user={"id": 1, "first_name": "Ada"},
        auth_date=1_700_000_000,
    )
    with pytest.raises(TelegramInitDataError) as exc:
        validate_init_data(
            init_data,
            BOT_TOKEN,
            max_age_seconds=60,
            now=datetime(2026, 9, 8, tzinfo=UTC),
        )
    assert exc.value.code == ErrorCode.TELEGRAM_INIT_DATA_EXPIRED
