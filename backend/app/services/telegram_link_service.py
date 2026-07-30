from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import AppError
from app.core.i18n import normalize_locale
from app.core.security import hash_token
from app.models.telegram_link_code import TelegramLinkCode
from app.models.user import User
from app.models.user_notification_settings import UserNotificationSettings
from app.services.notifications.base import NotificationChannel


class TelegramLinkError(AppError):
    pass


def bot_is_configured() -> bool:
    return bool(settings.telegram_bot_token.strip() and settings.telegram_bot_username.strip())


def serialize_link_status(user: User) -> dict[str, object]:
    username = settings.telegram_bot_username.strip() or None
    return {
        "linked": user.telegram_linked,
        "telegram_user_id": user.telegram_user_id,
        "telegram_linked_at": user.telegram_linked_at,
        "bot_username": username,
        "bot_configured": bot_is_configured(),
    }


def create_link_code(db: Session, *, user: User) -> tuple[str, TelegramLinkCode, str]:
    if not bot_is_configured():
        raise TelegramLinkError(
            "Telegram bot is not configured", code="telegram_bot_not_configured", status_code=503
        )
    if user.telegram_linked:
        raise TelegramLinkError(
            "Telegram is already linked. Unlink it before connecting another account.",
            code="telegram_already_linked",
            status_code=409,
        )

    # Telegram start payload max length is 64 characters.
    raw_code = secrets.token_urlsafe(18)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.telegram_link_code_expire_minutes,
    )

    db.execute(
        update(TelegramLinkCode)
        .where(
            TelegramLinkCode.user_id == user.id,
            TelegramLinkCode.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )

    row = TelegramLinkCode(
        user_id=user.id,
        code_hash=hash_token(raw_code),
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    username = settings.telegram_bot_username.strip()
    deep_link = f"https://t.me/{username}?start={raw_code}"
    return raw_code, row, deep_link


def link_telegram_account(
    db: Session,
    *,
    code: str,
    telegram_user_id: int,
    telegram_chat_id: int,
    locale: str | None = None,
) -> User:
    now = datetime.now(UTC)
    code_hash = hash_token(code.strip())
    row = db.scalar(
        select(TelegramLinkCode)
        .where(
            TelegramLinkCode.code_hash == code_hash,
            TelegramLinkCode.used_at.is_(None),
        )
        .order_by(TelegramLinkCode.created_at.desc())
    )
    if row is None:
        raise TelegramLinkError(
            "Invalid or already used link code", code="telegram_link_code_invalid", status_code=400
        )
    if row.expires_at <= now:
        raise TelegramLinkError(
            "Link code has expired", code="telegram_link_code_expired", status_code=400
        )

    user = db.get(User, row.user_id)
    if user is None:
        raise TelegramLinkError("User not found", code="user_not_found", status_code=404)
    if user.email_verified_at is None:
        raise TelegramLinkError(
            "User email is not verified", code="email_not_verified", status_code=403
        )

    existing = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if existing is not None and existing.id != user.id:
        raise TelegramLinkError(
            "This Telegram account is already linked to another user",
            code="telegram_account_linked_other_user",
            status_code=409,
        )
    if user.telegram_linked and user.telegram_user_id != telegram_user_id:
        raise TelegramLinkError(
            "This GlowPath account is already linked to another Telegram user",
            code="account_linked_other_telegram",
            status_code=409,
        )

    user.telegram_user_id = telegram_user_id
    user.telegram_chat_id = telegram_chat_id
    user.telegram_linked_at = now
    if locale:
        user.telegram_locale = normalize_locale(locale)

    row.used_at = now
    db.commit()
    db.refresh(user)
    return user


def unlink_telegram_account(db: Session, *, user: User) -> User:
    if not user.telegram_linked:
        raise TelegramLinkError(
            "Telegram is not linked", code="telegram_not_linked", status_code=404
        )

    user.telegram_user_id = None
    user.telegram_chat_id = None
    user.telegram_linked_at = None
    user.telegram_locale = None
    _remove_telegram_channel(db, user_id=user.id)
    db.commit()
    db.refresh(user)
    return user


def unlink_by_telegram_user_id(db: Session, *, telegram_user_id: int) -> User:
    user = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if user is None:
        raise TelegramLinkError(
            "Telegram account is not linked", code="telegram_not_linked", status_code=404
        )
    return unlink_telegram_account(db, user=user)


def get_user_by_telegram_id(db: Session, *, telegram_user_id: int) -> User | None:
    return db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))


def _remove_telegram_channel(db: Session, *, user_id: uuid.UUID) -> None:
    prefs = db.scalar(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    if prefs is None or not prefs.channels:
        return
    channel = NotificationChannel.TELEGRAM.value
    if channel not in prefs.channels:
        return
    remaining = [item for item in prefs.channels if item != channel]
    prefs.channels = remaining or [NotificationChannel.EMAIL.value]
