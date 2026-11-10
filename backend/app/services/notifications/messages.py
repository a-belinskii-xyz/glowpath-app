from __future__ import annotations

import html
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import settings
from app.core.companion import (
    daily_reminder_intro,
    daily_reminder_question,
    daily_reminder_subject,
)
from app.core.i18n import DEFAULT_LOCALE
from app.core.mood_entry_source import MoodEntryAttributionKind, format_mood_entry_source
from app.core.mood_scale import MoodScore, mood_score_emoji
from app.core.notification_copy import NotificationText as T
from app.core.notification_copy import notification_text
from app.core.telegram_quick_log import QuickTap, encode_quick_tap
from app.services.notifications.base import NotificationChannel, NotificationMessage

STARTAPP_CREATE = "create"
STARTAPP_CREATE_DAILY = "create_daily"
STARTAPP_GOAL_REMINDER = "goal_reminder"
STARTAPP_ONBOARDING = "onboarding"
# Opens the edit form of one entry; the Mini App reads it in platform/startParam.ts.
STARTAPP_EDIT_ENTRY_PREFIX = "edit_"


def daily_mood_reminder_message(
    *,
    channel: NotificationChannel,
    hour: int = 12,
    locale: str = DEFAULT_LOCALE,
    unsubscribe_token: str | None = None,
    tracking_token: str | None = None,
    variant_seed: str = "",
    display_name: str | None = None,
    score_faces: Mapping[int, str] | None = None,
) -> NotificationMessage:
    """Daily mood reminder.

    In Telegram it is a short question with a row of mood buttons that log the mood
    with one tap (see ``services/telegram_quick_log_service.py``); *score_faces* are the
    person's emoji for the buttons. In email it is a greeting and a link to the form.
    """
    source = format_mood_entry_source(
        channel=channel.value,
        kind=MoodEntryAttributionKind.DAILY_MOOD_REMINDER,
    )
    log_url = f"{settings.frontend_url.rstrip('/')}/entries/new?" + urlencode(
        _link_params(source=source, tracking_token=tracking_token)
    )
    subject = daily_reminder_subject(hour=hour, locale=locale)

    if channel is NotificationChannel.TELEGRAM:
        question = daily_reminder_question(
            hour=hour, locale=locale, seed=variant_seed, name=display_name
        )
        markup = quick_log_keyboard(
            locale=locale,
            faces=score_faces or default_score_faces(),
            token=tracking_token,
            from_reminder=True,
        )
        return NotificationMessage(
            subject=subject,
            body=question,
            html_body=None,
            metadata={
                "type": MoodEntryAttributionKind.DAILY_MOOD_REMINDER.value,
                "channel": channel.value,
                "source": source,
                "telegram_reply_markup": markup,
            },
        )

    intro = daily_reminder_intro(hour=hour, locale=locale, seed=variant_seed, name=display_name)
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


def default_score_faces() -> dict[int, str]:
    return {score.value: mood_score_emoji(score) for score in MoodScore}


def quick_log_keyboard(
    *,
    locale: str,
    faces: Mapping[int, str],
    token: str | None = None,
    selected: int | None = None,
    entry_id: uuid.UUID | None = None,
    can_undo: bool = False,
    from_reminder: bool | None = None,
) -> dict[str, Any]:
    """Mood buttons for logging with one tap, before or after the tap.

    Before (*selected* is None): the faces, then "Log in detail" into the Mini App form.
    After: the faces with the logged one marked, so another tap changes it, then "Note
    and tags" into the entry's edit form and, while allowed, "Undo".

    *token* is the reminder's delivery token. When *from_reminder* is not given, a
    keyboard with a token is taken to be a reminder's and one without to be ``/log``'s.
    """
    reminder = bool(token) if from_reminder is None else from_reminder
    faces_row = [
        {
            "text": f"•{faces[score.value]}•" if score.value == selected else faces[score.value],
            "callback_data": encode_quick_tap(QuickTap(score=score.value, token=token)),
        }
        for score in MoodScore
    ]
    rows: list[list[dict[str, Any]]] = [faces_row]
    if selected is None:
        more = telegram_app_button(
            startapp=STARTAPP_CREATE_DAILY if reminder else STARTAPP_CREATE,
            text=notification_text(T.QUICK_MORE_BUTTON, locale),
            tracking_token=token,
        )
        if more is not None:
            rows.append([more])
        return {"inline_keyboard": rows}

    actions: list[dict[str, Any]] = []
    if entry_id is not None:
        note = telegram_app_button(
            startapp=f"{STARTAPP_EDIT_ENTRY_PREFIX}{entry_id.hex}",
            text=notification_text(T.QUICK_NOTE_BUTTON, locale),
        )
        if note is not None:
            actions.append(note)
    if can_undo:
        actions.append(
            {
                "text": notification_text(T.QUICK_UNDO_BUTTON, locale),
                "callback_data": encode_quick_tap(QuickTap(score=None, token=token)),
            }
        )
    if actions:
        rows.append(actions)
    return {"inline_keyboard": rows}


def telegram_app_button(
    *,
    startapp: str,
    text: str,
    tracking_token: str | None = None,
) -> dict[str, Any] | None:
    """A button that opens the Mini App at *startapp*; None when the bot has no app."""
    mini = settings.telegram_mini_app_url.strip()
    if mini:
        url = _with_start_param(mini, startapp)
        if tracking_token:
            url = _with_query_param(url, "n", tracking_token)
        return {"text": text, "web_app": {"url": url}}
    deep = _telegram_mini_app_deep_link(startapp=startapp)
    if deep:
        return {"text": text, "url": deep}
    return None


def _telegram_open_markup(
    *,
    startapp: str,
    button_text: str,
    tracking_token: str | None = None,
) -> dict[str, Any] | None:
    button = telegram_app_button(
        startapp=startapp,
        text=button_text,
        tracking_token=tracking_token,
    )
    if button is None:
        return None
    return {"inline_keyboard": [[button]]}


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
