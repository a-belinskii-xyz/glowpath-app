from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification_settings import (
    NotificationSettingsPublic,
    NotificationSettingsUpdate,
)
from app.services.notification_settings_service import (
    NotificationSettingsError,
    get_or_create_settings,
    serialize_settings,
    update_settings,
)

router = APIRouter(tags=["notification-settings"])


@router.get("", response_model=NotificationSettingsPublic)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> NotificationSettingsPublic:
    prefs = get_or_create_settings(db, user_id=current_user.id)
    return NotificationSettingsPublic.model_validate(serialize_settings(prefs))


@router.patch("", response_model=NotificationSettingsPublic)
def patch_notification_settings(
    body: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> NotificationSettingsPublic:
    clear_time = (
        "daily_mood_reminder_time" in body.model_fields_set
        and body.daily_mood_reminder_time is None
    )
    try:
        prefs = update_settings(
            db,
            user_id=current_user.id,
            enabled=body.enabled,
            channels=body.channels,
            daily_mood_reminder_enabled=body.daily_mood_reminder_enabled,
            daily_mood_reminder_time=body.daily_mood_reminder_time,
            clear_daily_mood_reminder_time=clear_time,
            goal_reminders_enabled=body.goal_reminders_enabled,
        )
    except NotificationSettingsError as exc:
        raise_http_error(exc)
    return NotificationSettingsPublic.model_validate(serialize_settings(prefs))
