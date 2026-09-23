from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.i18n import normalize_locale
from app.core.telegram_init_data import TelegramInitDataError, validate_init_data
from app.core.timezones import normalize_timezone
from app.models.user import User
from app.services.auth_service import AuthError, TokenPair, issue_token_pair
from app.services.user_provisioning import (
    provision_default_goals,
    provision_default_note_templates,
    provision_default_tags,
    provision_mood_preferences,
    provision_notification_settings,
)


def authenticate_telegram_init_data(
    db: Session,
    *,
    init_data: str,
    timezone: str,
) -> TokenPair:
    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        raise AuthError(
            "Telegram bot is not configured",
            code=ErrorCode.TELEGRAM_BOT_NOT_CONFIGURED,
            status_code=503,
        )

    try:
        timezone_name = normalize_timezone(timezone)
    except ValueError as exc:
        raise AuthError(str(exc), code=ErrorCode.INVALID_TIMEZONE, status_code=400) from exc

    try:
        parsed = validate_init_data(
            init_data,
            bot_token,
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
        )
    except TelegramInitDataError as exc:
        raise AuthError(exc.message, code=exc.code, status_code=exc.status_code) from exc

    telegram_user_id = parsed.user.id
    locale = normalize_locale(parsed.user.language_code) if parsed.user.language_code else None
    now = datetime.now(UTC)

    existing = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if existing is not None:
        existing.telegram_chat_id = telegram_user_id
        if existing.telegram_linked_at is None:
            existing.telegram_linked_at = now
        if locale:
            existing.telegram_locale = locale
        db.commit()
        return issue_token_pair(existing.id)

    user = User(
        email=None,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_user_id,
        telegram_linked_at=now,
        telegram_locale=locale,
        timezone=timezone_name,
    )
    db.add(user)
    db.flush()
    provision_default_tags(db, user.id)
    provision_default_note_templates(db, user.id)
    provision_default_goals(db, user.id, starts_on=_local_today(timezone_name))
    provision_notification_settings(db, user.id)
    provision_mood_preferences(db, user.id)
    db.commit()
    return issue_token_pair(user.id, user_created=True)


def _local_today(timezone_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()
