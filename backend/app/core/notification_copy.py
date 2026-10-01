"""Fixed wording of reminder notifications (Telegram and email), per language.

Time-of-day phrases (subject and intro of the daily reminder) live in
``app.core.companion``. Everything else a reminder says is here, so changing the
wording means editing this one file. Texts are grouped by companion style, so a
new style only adds its own entries and falls back to the default for the rest.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion import CompanionStyle
from app.core.i18n import LocaleLabels, resolve_label


class NotificationText(StrEnum):
    GREETING = "greeting"
    DAILY_PROMPT = "daily_prompt"
    DAILY_BUTTON = "daily_button"
    DAILY_LINK = "daily_link"
    DAILY_FOOTER = "daily_footer"
    GOAL_SUBJECT = "goal_subject"
    GOAL_HEADING = "goal_heading"
    GOAL_BUTTON = "goal_button"
    GOAL_EMAIL_LEAD = "goal_email_lead"
    GOAL_LINK = "goal_link"
    GOAL_FOOTER = "goal_footer"
    PAUSED_SUBJECT = "paused_subject"
    PAUSED_TEXT = "paused_text"
    PAUSED_LINK = "paused_link"
    UNSUBSCRIBE = "unsubscribe"


_TEXTS: dict[CompanionStyle, dict[NotificationText, LocaleLabels]] = {
    CompanionStyle.DEFAULT: {
        NotificationText.GREETING: {
            "en": "Hi,",
            "ru": "Привет,",
        },
        NotificationText.DAILY_PROMPT: {
            "en": "Log your mood in GlowPath.",
            "ru": "Запиши настроение в GlowPath.",
        },
        NotificationText.DAILY_BUTTON: {
            "en": "Log mood",
            "ru": "Записать настроение",
        },
        NotificationText.DAILY_LINK: {
            "en": "Log your mood",
            "ru": "Записать настроение",
        },
        NotificationText.DAILY_FOOTER: {
            "en": "You can change reminder settings in your profile.",
            "ru": "Напоминания можно изменить в профиле.",
        },
        NotificationText.GOAL_SUBJECT: {
            "en": "Your weekly goals need attention",
            "ru": "Цели на неделю отстают",
        },
        NotificationText.GOAL_HEADING: {
            "en": "Some weekly goals are still behind:",
            "ru": "Некоторые цели на неделю ещё отстают:",
        },
        NotificationText.GOAL_BUTTON: {
            "en": "Open goals",
            "ru": "Открыть цели",
        },
        NotificationText.GOAL_EMAIL_LEAD: {
            "en": "Some of your GlowPath goals are still behind for this week:",
            "ru": "Некоторые цели в GlowPath на этой неделе ещё отстают:",
        },
        NotificationText.GOAL_LINK: {
            "en": "Review your goals",
            "ru": "Посмотреть цели",
        },
        NotificationText.GOAL_FOOTER: {
            "en": "You can turn goal reminders off in notification settings.",
            "ru": "Напоминания о целях можно выключить в настройках уведомлений.",
        },
        NotificationText.PAUSED_SUBJECT: {
            "en": "Pausing your reminders",
            "ru": "Ставим напоминания на паузу",
        },
        NotificationText.PAUSED_TEXT: {
            "en": (
                "It looks like reminders are not helpful right now, so we will stop sending "
                "them. Your diary is still here. Turn reminders back on in settings whenever "
                "you like."
            ),
            "ru": (
                "Похоже, напоминания сейчас не к месту, поэтому мы больше не будем их "
                "присылать. Дневник никуда не делся. Если захотите вернуть напоминания, "
                "включите их в настройках."
            ),
        },
        NotificationText.PAUSED_LINK: {
            "en": "Notification settings",
            "ru": "Настройки уведомлений",
        },
        NotificationText.UNSUBSCRIBE: {
            "en": "Unsubscribe from emails",
            "ru": "Отписаться от писем",
        },
    },
}


def notification_text(
    key: NotificationText,
    locale: str,
    *,
    style: CompanionStyle = CompanionStyle.DEFAULT,
) -> str:
    labels = _TEXTS.get(style, {}).get(key) or _TEXTS[CompanionStyle.DEFAULT][key]
    return resolve_label(labels, locale)
