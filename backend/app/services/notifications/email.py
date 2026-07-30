from __future__ import annotations

from app.services.email_service import EmailService
from app.services.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationError,
    NotificationMessage,
    SentNotification,
)


class EmailNotifier(BaseNotifier):
    """Delivers notifications via the shared SMTP ``EmailService``."""

    def __init__(self, email_service: EmailService) -> None:
        self._email_service = email_service

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    def send(self, *, recipient: str, message: NotificationMessage) -> SentNotification:
        if not recipient.strip():
            raise NotificationError(
                "Email recipient is empty",
                code="email_recipient_empty",
                status_code=400,
            )
        try:
            self._email_service.send(
                to=recipient,
                subject=message.subject,
                body=message.body,
                html_body=message.html_body,
            )
        except OSError as exc:
            raise NotificationError(
                f"Failed to send email notification: {exc}",
                code="email_send_failed",
                status_code=502,
            ) from exc
        return SentNotification(
            channel=NotificationChannel.EMAIL,
            recipient=recipient,
            subject=message.subject,
            body=message.body,
        )
