import pytest
from app.services.notifications import (
    BaseNotifier,
    FakeNotifier,
    NotificationChannel,
    NotificationMessage,
)


def test_base_notifier_requires_channel_and_send() -> None:
    notifier = BaseNotifier()

    with pytest.raises(NotImplementedError):
        _ = notifier.channel

    with pytest.raises(NotImplementedError):
        notifier.send(
            recipient="user@example.com",
            message=NotificationMessage(subject="Hi", body="Hello"),
        )


def test_fake_notifier_records_outbox() -> None:
    notifier = FakeNotifier(channel=NotificationChannel.TELEGRAM)
    message = NotificationMessage(subject="Reminder", body="Log your mood")

    sent = notifier.send(recipient="123456", message=message)

    assert sent.channel is NotificationChannel.TELEGRAM
    assert sent.recipient == "123456"
    assert sent.subject == "Reminder"
    assert sent.body == "Log your mood"
    assert notifier.outbox == [sent]

    notifier.clear_outbox()
    assert notifier.outbox == []
