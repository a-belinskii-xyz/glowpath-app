from __future__ import annotations

from urllib.parse import urlencode

from app.config import settings
from app.core.companion import daily_reminder_intro, daily_reminder_subject
from app.core.i18n import DEFAULT_LOCALE
from app.core.mood_entry_source import MoodEntryAttributionKind, format_mood_entry_source
from app.services.notifications.base import NotificationChannel, NotificationMessage


def daily_mood_reminder_message(
    *,
    channel: NotificationChannel,
    hour: int = 12,
    locale: str = DEFAULT_LOCALE,
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.DAILY_MOOD_REMINDER,
    )
    log_url = f"{settings.frontend_url.rstrip('/')}/entries/new?{urlencode({'from': source})}"
    bot_url = _telegram_bot_deep_link(start="log")
    subject = daily_reminder_subject(hour=hour, locale=locale)
    intro = daily_reminder_intro(hour=hour, locale=locale)

    if channel is NotificationChannel.TELEGRAM:
        lines = [
            intro,
            "",
            "Log your mood in GlowPath." if locale != "ru" else "Запиши настроение в GlowPath.",
            "",
            f"Open the app: {log_url}" if locale != "ru" else f"Открыть приложение: {log_url}",
        ]
        if bot_url:
            or_bot = (
                f"Or continue in the bot: {bot_url}"
                if locale != "ru"
                else f"Или продолжить в боте: {bot_url}"
            )
            lines.extend(["", or_bot])
        body = "\n".join(lines)
        return NotificationMessage(
            subject=subject,
            body=body,
            html_body=None,
            metadata={
                "type": MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value,
                "channel": channel.value,
                "source": source,
            },
        )

    if locale == "ru":
        body = (
            "Привет,\n\n"
            f"{intro}\n\n"
            f"Записать настроение: {log_url}\n\n"
            "Напоминания можно изменить в профиле.\n"
        )
        html_body = (
            "<p>Привет,</p>"
            f"<p>{intro}</p>"
            f'<p><a href="{log_url}">Записать настроение</a></p>'
            "<p>Напоминания можно изменить в профиле.</p>"
        )
    else:
        body = (
            "Hi,\n\n"
            f"{intro}\n\n"
            f"Log your mood: {log_url}\n\n"
            "You can change reminder settings in your profile.\n"
        )
        html_body = (
            "<p>Hi,</p>"
            f"<p>{intro}</p>"
            f'<p><a href="{log_url}">Log your mood</a></p>'
            "<p>You can change reminder settings in your profile.</p>"
        )
    return NotificationMessage(
        subject=subject,
        body=body,
        html_body=html_body,
        metadata={
            "type": MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value,
            "channel": channel.value,
            "source": source,
        },
    )


def goal_reminder_message(
    *,
    channel: NotificationChannel,
    goal_labels: list[str],
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.GOAL_REMINDER,
    )
    home_url = f"{settings.frontend_url.rstrip('/')}/?{urlencode({'from': source})}"
    bot_url = _telegram_bot_deep_link(start="log")
    bullet_lines = "\n".join(f"  • {label}" for label in goal_labels)
    subject = "Your weekly goals need attention"

    if channel is NotificationChannel.TELEGRAM:
        lines = [
            "Some weekly goals are still behind:",
            "",
            bullet_lines,
            "",
            f"Open GlowPath: {home_url}",
        ]
        if bot_url:
            lines.extend(["", f"Or continue in the bot: {bot_url}"])
        body = "\n".join(lines)
        return NotificationMessage(
            subject=subject,
            body=body,
            html_body=None,
            metadata={
                "type": MoodEntryAttributionKind.GOAL_REMINDER.value,
                "channel": channel.value,
                "source": source,
                "goals": goal_labels,
            },
        )

    body = (
        "Hi,\n\n"
        "Some of your GlowPath goals are still behind for this week:\n\n"
        f"{bullet_lines}\n\n"
        f"Review your goals: {home_url}\n\n"
        "You can turn goal reminders off in notification settings.\n"
    )
    items = "".join(f"<li>{label}</li>" for label in goal_labels)
    html_body = (
        "<p>Hi,</p>"
        "<p>Some of your GlowPath goals are still behind for this week:</p>"
        f"<ul>{items}</ul>"
        f'<p><a href="{home_url}">Open GlowPath</a></p>'
        "<p>You can turn goal reminders off in notification settings.</p>"
    )
    return NotificationMessage(
        subject=subject,
        body=body,
        html_body=html_body,
        metadata={
            "type": MoodEntryAttributionKind.GOAL_REMINDER.value,
            "channel": channel.value,
            "source": source,
            "goals": goal_labels,
        },
    )


def _telegram_bot_deep_link(*, start: str) -> str | None:
    username = settings.telegram_bot_username.strip()
    if not username:
        return None
    return f"https://t.me/{username}?start={start}"
