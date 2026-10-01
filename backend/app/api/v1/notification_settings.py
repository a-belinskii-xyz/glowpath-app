import jwt
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_verified_user, get_locale
from app.core.error_codes import ErrorCode
from app.core.errors import AppError, raise_http_error
from app.core.security import decode_email_unsubscribe_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification_settings import (
    NotificationScheduleUpdate,
    NotificationSettingsPublic,
    NotificationSystemStatus,
    UnsubscribeResponse,
)
from app.services.notification_settings_service import (
    NotificationSettingsError,
    list_settings,
    unsubscribe_email,
    update_schedule,
)
from app.services.notifications.backoff import mark_engaged
from app.services.notifications.worker_status import system_status

router = APIRouter(tags=["notification-settings"])


@router.get("/status", response_model=NotificationSystemStatus)
def get_notification_status(
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    _: User = Depends(get_current_user),
) -> NotificationSystemStatus:
    return system_status(db, locale=locale)


@router.post("/unsubscribe", response_model=UnsubscribeResponse)
def post_unsubscribe(
    token: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> UnsubscribeResponse:
    """Turn off email reminders from a signed link; no session needed.

    Also serves RFC 8058 one-click unsubscribe (``List-Unsubscribe-Post``), where the
    mail provider POSTs to the URL from the ``List-Unsubscribe`` header.
    """
    try:
        user_id = decode_email_unsubscribe_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise_http_error(
            AppError("Invalid unsubscribe link", code=ErrorCode.INVALID_TOKEN, status_code=400)
        )
    unsubscribe_email(db, user_id=user_id)
    return UnsubscribeResponse(unsubscribed=True)


@router.post("/engaged", status_code=204)
def post_engaged(
    token: str = Query(min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> None:
    """Record that a reminder link was followed (``?n=`` from email or Telegram)."""
    mark_engaged(db, token=token)


@router.get("", response_model=NotificationSettingsPublic)
def get_notification_settings(
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    current_user: User = Depends(get_current_verified_user),
) -> NotificationSettingsPublic:
    return list_settings(db, user_id=current_user.id, locale=locale)


@router.patch("/{kind}", response_model=NotificationSettingsPublic)
def patch_notification_schedule(
    kind: str,
    body: NotificationScheduleUpdate,
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    current_user: User = Depends(get_current_verified_user),
) -> NotificationSettingsPublic:
    try:
        return update_schedule(
            db,
            user_id=current_user.id,
            kind=kind,
            body=body,
            locale=locale,
        )
    except NotificationSettingsError as exc:
        raise_http_error(exc)
