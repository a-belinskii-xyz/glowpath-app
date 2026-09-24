from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.i18n import normalize_locale
from app.core.telegram_init_data import TelegramInitDataError, validate_init_data
from app.core.telegram_oidc import (
    build_authorization_url,
    decode_id_token,
    exchange_authorization_code,
    generate_oidc_state,
    generate_pkce_pair,
    telegram_oidc_configured,
)
from app.core.timezones import normalize_timezone
from app.models.user import User
from app.services.auth_service import (
    AuthError,
    TokenPair,
    _link_pending_guest_device,
    _mark_existing_login_skipped,
    issue_token_pair,
)
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

    locale = normalize_locale(parsed.user.language_code) if parsed.user.language_code else None
    return login_or_create_telegram_user(
        db,
        telegram_user_id=parsed.user.id,
        timezone=timezone_name,
        locale=locale,
    )


def begin_telegram_browser_login(*, timezone: str) -> tuple[str, str, str, str]:
    """Return authorization URL, OIDC state, PKCE verifier, and normalized timezone."""
    _require_oidc_config()
    timezone_name = _timezone_or_error(timezone)
    verifier, challenge = generate_pkce_pair()
    state = generate_oidc_state()
    url = build_authorization_url(
        client_id=settings.telegram_oidc_client_id.strip(),
        redirect_uri=settings.telegram_oidc_redirect_uri,
        state=state,
        code_challenge=challenge,
    )
    return url, state, verifier, timezone_name


def complete_telegram_browser_login(
    db: Session,
    *,
    code: str,
    code_verifier: str,
    timezone: str,
    visitor_id: uuid.UUID | None = None,
) -> TokenPair:
    _require_oidc_config()
    timezone_name = _timezone_or_error(timezone)
    id_token = exchange_authorization_code(
        code=code,
        client_id=settings.telegram_oidc_client_id.strip(),
        client_secret=settings.telegram_oidc_client_secret,
        redirect_uri=settings.telegram_oidc_redirect_uri,
        code_verifier=code_verifier,
    )
    profile = decode_id_token(id_token, client_id=settings.telegram_oidc_client_id.strip())
    return login_or_create_telegram_user(
        db,
        telegram_user_id=profile.telegram_user_id,
        timezone=timezone_name,
        locale=None,
        visitor_id=visitor_id,
    )


def login_or_create_telegram_user(
    db: Session,
    *,
    telegram_user_id: int,
    timezone: str,
    locale: str | None,
    visitor_id: uuid.UUID | None = None,
) -> TokenPair:
    now = datetime.now(UTC)
    existing = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if existing is not None:
        existing.telegram_chat_id = telegram_user_id
        if existing.telegram_linked_at is None:
            existing.telegram_linked_at = now
        if locale:
            existing.telegram_locale = locale
        _mark_existing_login_skipped(db, user=existing, visitor_id=visitor_id)
        db.commit()
        return issue_token_pair(existing.id)

    user = User(
        email=None,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_user_id,
        telegram_linked_at=now,
        telegram_locale=locale,
        timezone=timezone,
    )
    db.add(user)
    db.flush()
    provision_default_tags(db, user.id)
    provision_default_note_templates(db, user.id)
    provision_default_goals(db, user.id, starts_on=_local_today(timezone))
    provision_notification_settings(db, user.id)
    provision_mood_preferences(db, user.id)
    _link_pending_guest_device(db, user=user, visitor_id=visitor_id)
    db.commit()
    return issue_token_pair(user.id, user_created=True)


def _require_oidc_config() -> None:
    if not telegram_oidc_configured(
        client_id=settings.telegram_oidc_client_id,
        client_secret=settings.telegram_oidc_client_secret,
    ):
        raise AuthError(
            "Telegram browser login is not configured",
            code=ErrorCode.TELEGRAM_OIDC_NOT_CONFIGURED,
            status_code=503,
        )


def _timezone_or_error(timezone: str) -> str:
    try:
        return normalize_timezone(timezone)
    except ValueError as exc:
        raise AuthError(str(exc), code=ErrorCode.INVALID_TIMEZONE, status_code=400) from exc


def _local_today(timezone_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(UTC).date()
