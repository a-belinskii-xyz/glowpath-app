from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import settings
from app.core.companion import daily_reminder_intro, daily_reminder_subject
from app.core.i18n import DEFAULT_LOCALE
from app.core.mood_entry_source import MoodEntryAttributionKind, format_mood_entry_source
from app.services.notifications.base import NotificationChannel, NotificationMessage

STARTAPP_CREATE_DAILY = "create_daily"
STARTAPP_GOAL_REMINDER = "goal_reminder"


def daily_mood_reminder_message(
    *,
    channel: NotificationChannel,
    hour: int = 12,
    locale: str = DEFAULT_LOCALE,
    unsubscribe_token: str | None = None,
    tracking_token: str | None = None,
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.DAILY_MOOD_REMINDER,
    )
    log_url = f"{settings.frontend_url.rstrip('/')}/entries/new?" + urlencode(
        _link_params(source=source, tracking_token=tracking_token)
    )
    subject = daily_reminder_subject(hour=hour, locale=locale)
    intro = daily_reminder_intro(hour=hour, locale=locale)

    if channel is NotificationChannel.TELEGRAM:
        prompt = "Log your mood in GlowPath." if locale != "ru" else "Запиши настроение в GlowPath."
        button = "Log mood" if locale != "ru" else "Записать настроение"
        markup = _telegram_open_markup(
            startapp=STARTAPP_CREATE_DAILY,
            button_text=button,
            tracking_token=tracking_token,
        )
        return NotificationMessage(
            subject=subject,
            body=f"{intro}\n\n{prompt}",
            html_body=None,
            metadata={
                "type": MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value,
                "channel": channel.value,
                "source": source,
                "telegram_reply_markup": markup,
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
    body, html_body, metadata = _with_unsubscribe(
        body=body,
        html_body=html_body,
        metadata={
            "type": MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value,
            "channel": channel.value,
            "source": source,
        },
        token=unsubscribe_token,
        locale=locale,
    )
    return NotificationMessage(subject=subject, body=body, html_body=html_body, metadata=metadata)


def goal_reminder_message(
    *,
    channel: NotificationChannel,
    goal_labels: list[str],
    locale: str = DEFAULT_LOCALE,
    unsubscribe_token: str | None = None,
    tracking_token: str | None = None,
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.GOAL_REMINDER,
    )
    goals_url = f"{settings.frontend_url.rstrip('/')}/goals?" + urlencode(
        _link_params(source=source, tracking_token=tracking_token)
    )
    bullet_lines = "\n".join(f"  • {label}" for label in goal_labels)
    subject = "Your weekly goals need attention" if locale != "ru" else "Цели на неделю отстают"

    if channel is NotificationChannel.TELEGRAM:
        heading = (
            "Some weekly goals are still behind:"
            if locale != "ru"
            else "Некоторые цели на неделю ещё отстают:"
        )
        button = "Open goals" if locale != "ru" else "Открыть цели"
        markup = _telegram_open_markup(
            startapp=STARTAPP_GOAL_REMINDER,
            button_text=button,
            tracking_token=tracking_token,
        )
        body = f"{heading}\n\n{bullet_lines}"
        return NotificationMessage(
            subject=subject,
            body=body,
            html_body=None,
            metadata={
                "type": MoodEntryAttributionKind.GOAL_REMINDER.value,
                "channel": channel.value,
                "source": source,
                "goals": goal_labels,
                "telegram_reply_markup": markup,
            },
        )

    body = (
        "Hi,\n\n"
        "Some of your GlowPath goals are still behind for this week:\n\n"
        f"{bullet_lines}\n\n"
        f"Review your goals: {goals_url}\n\n"
        "You can turn goal reminders off in notification settings.\n"
    )
    items = "".join(f"<li>{label}</li>" for label in goal_labels)
    html_body = (
        "<p>Hi,</p>"
        "<p>Some of your GlowPath goals are still behind for this week:</p>"
        f"<ul>{items}</ul>"
        f'<p><a href="{goals_url}">Review your goals</a></p>'
        "<p>You can turn goal reminders off in notification settings.</p>"
    )
    body, html_body, metadata = _with_unsubscribe(
        body=body,
        html_body=html_body,
        metadata={
            "type": MoodEntryAttributionKind.GOAL_REMINDER.value,
            "channel": channel.value,
            "source": source,
            "goals": goal_labels,
        },
        token=unsubscribe_token,
        locale=locale,
    )
    return NotificationMessage(subject=subject, body=body, html_body=html_body, metadata=metadata)


def unsubscribe_page_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/unsubscribe?{urlencode({'token': token})}"


def one_click_unsubscribe_url(token: str) -> str:
    # The web frontend proxies /v1 to the API, so one public origin serves both.
    base = settings.frontend_url.rstrip("/")
    return f"{base}/v1/notification-settings/unsubscribe?{urlencode({'token': token})}"


def _with_unsubscribe(
    *,
    body: str,
    html_body: str,
    metadata: dict[str, Any],
    token: str | None,
    locale: str,
) -> tuple[str, str, dict[str, Any]]:
    """Append an unsubscribe link and RFC 8058 headers to a reminder email."""
    if not token:
        return body, html_body, metadata
    page_url = unsubscribe_page_url(token)
    label = "Отписаться от писем" if locale == "ru" else "Unsubscribe from emails"
    body = f"{body}\n{label}: {page_url}\n"
    html_body = (
        f'{html_body}<p style="font-size:12px;color:#888"><a href="{page_url}">{label}</a></p>'
    )
    metadata = {
        **metadata,
        "email_headers": {
            "List-Unsubscribe": f"<{one_click_unsubscribe_url(token)}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }
    return body, html_body, metadata


def reminders_paused_message(
    *,
    channel: NotificationChannel,
    locale: str = DEFAULT_LOCALE,
    unsubscribe_token: str | None = None,
) -> NotificationMessage:
    """Last message before a schedule pauses itself after ignored reminders."""
    settings_url = f"{settings.frontend_url.rstrip('/')}/settings/notifications"
    if locale == "ru":
        subject = "Ставим напоминания на паузу"
        text = (
            "Похоже, напоминания сейчас не к месту, поэтому мы больше не будем их присылать. "
            "Дневник никуда не делся. Если захотите вернуть напоминания, включите их в настройках."
        )
        link_label = "Настройки уведомлений"
    else:
        subject = "Pausing your reminders"
        text = (
            "It looks like reminders are not helpful right now, so we will stop sending them. "
            "Your diary is still here. Turn reminders back on in settings whenever you like."
        )
        link_label = "Notification settings"
    metadata: dict[str, Any] = {"type": "reminders_paused", "channel": channel.value}
    if channel is NotificationChannel.TELEGRAM:
        return NotificationMessage(subject=subject, body=text, html_body=None, metadata=metadata)
    body = f"{text}\n\n{link_label}: {settings_url}\n"
    html_body = f'<p>{text}</p><p><a href="{settings_url}">{link_label}</a></p>'
    body, html_body, metadata = _with_unsubscribe(
        body=body,
        html_body=html_body,
        metadata=metadata,
        token=unsubscribe_token,
        locale=locale,
    )
    return NotificationMessage(subject=subject, body=body, html_body=html_body, metadata=metadata)


def _link_params(*, source: str, tracking_token: str | None) -> dict[str, str]:
    params = {"from": source}
    if tracking_token:
        # Read by the web app to record that the reminder was followed (see backoff.py).
        params["n"] = tracking_token
    return params


def _telegram_open_markup(
    *,
    startapp: str,
    button_text: str,
    tracking_token: str | None = None,
) -> dict[str, Any] | None:
    mini = settings.telegram_mini_app_url.strip()
    if mini:
        url = _with_start_param(mini, startapp)
        if tracking_token:
            url = _with_query_param(url, "n", tracking_token)
        return {"inline_keyboard": [[{"text": button_text, "web_app": {"url": url}}]]}
    deep = _telegram_mini_app_deep_link(startapp=startapp)
    if deep:
        return {"inline_keyboard": [[{"text": button_text, "url": deep}]]}
    return None


def _with_start_param(url: str, start: str) -> str:
    return _with_query_param(url, "tgWebAppStartParam", start)


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunparse(parts._replace(query=urlencode(query)))


def _telegram_mini_app_deep_link(*, startapp: str) -> str | None:
    username = settings.telegram_bot_username.strip()
    if not username:
        return None
    return f"https://t.me/{username}?startapp={startapp}"
