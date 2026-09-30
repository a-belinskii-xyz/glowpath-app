"""Endpoints for trusted infrastructure callers, not for app users."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_codes import ErrorCode
from app.core.errors import structured_detail
from app.db.session import get_db
from app.schemas.notification_settings import ReminderTickResponse
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.factory import build_notification_dispatcher
from app.services.notifications.tick import run_reminder_tick

router = APIRouter(tags=["internal"])


def require_cron_secret(authorization: str | None = Header(default=None)) -> None:
    expected = settings.reminders_cron_secret.strip()
    if not expected:
        # Unconfigured = the endpoint does not exist for the outside world.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        token.strip().encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=structured_detail(
                code=ErrorCode.INVALID_CRON_SECRET,
                message="Invalid cron secret",
            ),
        )


def get_notification_dispatcher() -> NotificationDispatcher:
    return build_notification_dispatcher()


@router.post(
    "/reminders/tick",
    response_model=ReminderTickResponse,
    dependencies=[Depends(require_cron_secret)],
)
def reminders_tick(
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> ReminderTickResponse:
    """Send due reminders once. Called every few minutes by cron-job.org."""
    result = run_reminder_tick(db, dispatcher)
    stats = result.stats
    return ReminderTickResponse(
        outcome=result.outcome,
        users_considered=stats.users_considered,
        daily_mood_sent=stats.daily_mood_sent,
        goal_reminders_sent=stats.goal_reminders_sent,
        skipped=stats.skipped,
        errors=len(stats.errors),
    )
