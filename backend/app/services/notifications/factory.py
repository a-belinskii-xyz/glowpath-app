from __future__ import annotations

from app.services.email_service import EmailService, email_service
from app.services.notifications.base import NotificationChannel
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.email import EmailNotifier


def build_notification_dispatcher(
    mailer: EmailService | None = None,
) -> NotificationDispatcher:
    """Build the default channel dispatcher (email today; more channels later)."""
    service = mailer if mailer is not None else email_service
    return NotificationDispatcher(
        {
            NotificationChannel.EMAIL: EmailNotifier(service),
        }
    )


notification_dispatcher = build_notification_dispatcher()
