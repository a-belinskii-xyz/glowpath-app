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
    # Logging a mood with one tap in the Telegram chat (see core/telegram_quick_log.py).
    QUICK_PROMPT = "quick_prompt"
    QUICK_MORE_BUTTON = "quick_more_button"
    QUICK_LOGGED = "quick_logged"
    QUICK_ACHIEVEMENT = "quick_achievement"
    QUICK_NOTE_BUTTON = "quick_note_button"
    QUICK_UNDO_BUTTON = "quick_undo_button"
    QUICK_SAVED_TOAST = "quick_saved_toast"
    QUICK_CHANGED_TOAST = "quick_changed_toast"
    QUICK_UNDONE_TOAST = "quick_undone_toast"
    QUICK_UNDO_EXPIRED_TOAST = "quick_undo_expired_toast"
    QUICK_STALE_TOAST = "quick_stale_toast"
    QUICK_NOT_LINKED = "quick_not_linked"
    QUICK_OPEN_BUTTON = "quick_open_button"


_TEXTS: dict[CompanionStyle, dict[NotificationText, LocaleLabels]] = {
    CompanionStyle.DEFAULT: {
        NotificationText.GREETING: {
            "en": "Hi,",
            "ru": "Привет,",
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
                "присылать. Дневник никуда не делся. Если захочешь вернуть напоминания, "
                "включи их в настройках."
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
        NotificationText.QUICK_PROMPT: {
            "en": "How are you right now?",
            "ru": "Как ты сейчас?",
        },
        NotificationText.QUICK_MORE_BUTTON: {
            "en": "✏️ Log in detail",
            "ru": "✏️ Записать подробнее",
        },
        NotificationText.QUICK_LOGGED: {
            "en": "Logged: {mood} · {time}",
            "ru": "Записано: {mood} · {time}",
        },
        NotificationText.QUICK_ACHIEVEMENT: {
            "en": "🏆 New achievement: {name}",
            "ru": "🏆 Новое достижение: {name}",
        },
        NotificationText.QUICK_NOTE_BUTTON: {
            "en": "✏️ Note and tags",
            "ru": "✏️ Заметка и теги",
        },
        NotificationText.QUICK_UNDO_BUTTON: {
            "en": "↩️ Undo",
            "ru": "↩️ Отменить",
        },
        NotificationText.QUICK_SAVED_TOAST: {
            "en": "Logged",
            "ru": "Записано",
        },
        NotificationText.QUICK_CHANGED_TOAST: {
            "en": "Mood changed",
            "ru": "Настроение изменено",
        },
        NotificationText.QUICK_UNDONE_TOAST: {
            "en": "Entry removed",
            "ru": "Запись удалена",
        },
        NotificationText.QUICK_UNDO_EXPIRED_TOAST: {
            "en": "You can delete this entry in the app now",
            "ru": "Эту запись теперь можно удалить только в приложении",
        },
        NotificationText.QUICK_STALE_TOAST: {
            "en": "This button no longer works. Send /log",
            "ru": "Эта кнопка больше не работает. Отправь /log",
        },
        NotificationText.QUICK_NOT_LINKED: {
            "en": "Open GlowPath first. Setup takes about a minute.",
            "ru": "Сначала открой GlowPath. Настройка займёт около минуты.",
        },
        NotificationText.QUICK_OPEN_BUTTON: {
            "en": "Open GlowPath",
            "ru": "Открыть GlowPath",
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
