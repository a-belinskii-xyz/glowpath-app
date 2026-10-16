from __future__ import annotations

import html
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import settings
from app.core.companion import daily_reminder_intro, daily_reminder_subject
from app.core.i18n import DEFAULT_LOCALE
from app.core.mood_entry_source import MoodEntryAttributionKind, format_mood_entry_source
from app.core.notification_copy import NotificationText as T
from app.core.notification_copy import notification_text
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
    variant_seed: str = "",
    display_name: str | None = None,
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.DAILY_MOOD_REMINDER,
    )
    log_url = f"{settings.frontend_url.rstrip('/')}/entries/new?" + urlencode(
        _link_params(source=source, tracking_token=tracking_token)
    )
    subject = daily_reminder_subject(hour=hour, locale=locale)
    intro = daily_reminder_intro(hour=hour, locale=locale, seed=variant_seed, name=display_name)

    if channel is NotificationChannel.TELEGRAM:
        prompt = notification_text(T.DAILY_PROMPT, locale)
        button = notification_text(T.DAILY_BUTTON, locale)
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

    greeting = _greeting(locale, display_name)
    link_label = notification_text(T.DAILY_LINK, locale)
    footer = notification_text(T.DAILY_FOOTER, locale)
    body = f"{greeting}\n\n{intro}\n\n{link_label}: {log_url}\n\n{footer}\n"
    html_body = (
        f"<p>{html.escape(greeting)}</p><p>{html.escape(intro)}</p>"
        f'<p><a href="{log_url}">{link_label}</a></p><p>{footer}</p>'
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


def _greeting(locale: str, display_name: str | None) -> str:
    """'Hi,' on its own, or 'Hi, Anna,' when the user gave a name."""
    greeting = notification_text(T.GREETING, locale)
    if not display_name:
        return greeting
    return f"{greeting.rstrip(',')}, {display_name},"


def goal_reminder_message(
    *,
    channel: NotificationChannel,
    goal_labels: list[str],
    locale: str = DEFAULT_LOCALE,
    unsubscribe_token: str | None = None,
    tracking_token: str | None = None,
    display_name: str | None = None,
) -> NotificationMessage:
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.GOAL_REMINDER,
    )
    goals_url = f"{settings.frontend_url.rstrip('/')}/goals?" + urlencode(
        _link_params(source=source, tracking_token=tracking_token)
    )
    bullet_lines = "\n".join(f"  • {label}" for label in goal_labels)
    subject = notification_text(T.GOAL_SUBJECT, locale)

    if channel is NotificationChannel.TELEGRAM:
        heading = notification_text(T.GOAL_HEADING, locale)
        button = notification_text(T.GOAL_BUTTON, locale)
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

    greeting = _greeting(locale, display_name)
    lead = notification_text(T.GOAL_EMAIL_LEAD, locale)
    link_label = notification_text(T.GOAL_LINK, locale)
    footer = notification_text(T.GOAL_FOOTER, locale)
    body = f"{greeting}\n\n{lead}\n\n{bullet_lines}\n\n{link_label}: {goals_url}\n\n{footer}\n"
    items = "".join(f"<li>{label}</li>" for label in goal_labels)
    html_body = (
        f"<p>{html.escape(greeting)}</p>"
        f"<p>{lead}</p>"
        f"<ul>{items}</ul>"
        f'<p><a href="{goals_url}">{link_label}</a></p>'
        f"<p>{footer}</p>"
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
    label = notification_text(T.UNSUBSCRIBE, locale)
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
    subject = notification_text(T.PAUSED_SUBJECT, locale)
    text = notification_text(T.PAUSED_TEXT, locale)
    link_label = notification_text(T.PAUSED_LINK, locale)
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
