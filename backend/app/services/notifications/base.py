from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.errors import AppError


class NotificationChannel(StrEnum):
    EMAIL = "email"
    TELEGRAM = "telegram"


class NotificationError(AppError):
    pass


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """Channel-agnostic payload shared by all notifiers."""

    subject: str
    body: str
    html_body: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SentNotification:
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str


class BaseNotifier:
    """Abstract base for a single delivery channel (email, Telegram, …).

    Subclasses must implement ``channel`` and ``send``. The ``recipient`` is a
    channel-specific address string (email, Telegram chat id, …).
    """

    @property
    def channel(self) -> NotificationChannel:
        raise NotImplementedError

    def send(self, *, recipient: str, message: NotificationMessage) -> SentNotification:
        raise NotImplementedError


class FakeNotifier(BaseNotifier):
    """In-memory notifier for tests and local development."""

    def __init__(self, *, channel: NotificationChannel = NotificationChannel.EMAIL) -> None:
        self._channel = channel
        self._outbox: list[SentNotification] = []

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @property
    def outbox(self) -> list[SentNotification]:
        return list(self._outbox)

    def clear_outbox(self) -> None:
        self._outbox.clear()

    def send(self, *, recipient: str, message: NotificationMessage) -> SentNotification:
        sent = SentNotification(
            channel=self._channel,
            recipient=recipient,
            subject=message.subject,
            body=message.body,
        )
        self._outbox.append(sent)
        return sent
