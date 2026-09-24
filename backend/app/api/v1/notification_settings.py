from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_verified_user, get_locale
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification_settings import (
    NotificationScheduleUpdate,
    NotificationSettingsPublic,
    NotificationSystemStatus,
)
from app.services.notification_settings_service import (
    NotificationSettingsError,
    list_settings,
    update_schedule,
)
from app.services.notifications.worker_status import system_status

router = APIRouter(tags=["notification-settings"])


@router.get("/status", response_model=NotificationSystemStatus)
def get_notification_status(
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    _: User = Depends(get_current_user),
) -> NotificationSystemStatus:
    return system_status(db, locale=locale)


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
