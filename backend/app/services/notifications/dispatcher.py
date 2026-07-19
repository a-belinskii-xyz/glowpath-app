from __future__ import annotations

from collections.abc import Mapping

from app.models.user import User
from app.services.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationError,
    NotificationMessage,
    SentNotification,
)


class NotificationDispatcher:
    """Routes a message to one or more channel notifiers."""

    def __init__(self, notifiers: Mapping[NotificationChannel, BaseNotifier]) -> None:
        self._notifiers = dict(notifiers)

    @property
    def supported_channels(self) -> frozenset[NotificationChannel]:
        return frozenset(self._notifiers)

    def send(
        self,
        *,
        user: User,
        channels: list[NotificationChannel],
        message: NotificationMessage,
    ) -> list[SentNotification]:
        if not channels:
            raise NotificationError(
                "At least one notification channel is required", status_code=400
            )

        sent: list[SentNotification] = []
        for channel in channels:
            notifier = self._notifiers.get(channel)
            if notifier is None:
                raise NotificationError(
                    f"Notification channel is not configured: {channel}",
                    status_code=501,
                )
            recipient = self._recipient_for(user, channel)
            sent.append(notifier.send(recipient=recipient, message=message))
        return sent

    def _recipient_for(self, user: User, channel: NotificationChannel) -> str:
        if channel is NotificationChannel.EMAIL:
            return user.email
        if channel is NotificationChannel.TELEGRAM:
            if user.telegram_chat_id is None:
                raise NotificationError(
                    "Telegram is not linked for this user",
                    status_code=400,
                )
            return str(user.telegram_chat_id)
        raise NotificationError(
            f"No recipient mapping for channel: {channel}",
            status_code=501,
        )
