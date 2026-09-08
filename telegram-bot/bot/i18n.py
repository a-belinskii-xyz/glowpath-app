from __future__ import annotations

from typing import Any

from bot.companion import companion_key
from bot.companion_i18n import COMPANION_MESSAGES

_BASE_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "help": (
            "GlowPath bot\n\n"
            "Open the app from the menu or the button below. New users set up "
            "the tracker in the app — the website is optional.\n\n"
            "Commands:\n"
            "/log — log your mood in the app\n"
            "/start <code> — link a website account\n"
            "/unlink — disconnect Telegram\n"
            "/help — show this message"
        ),
        "already_linked": (
            "Your Telegram is already linked to GlowPath.\n"
            "Open the app to check in."
        ),
        "need_link": (
            "Open GlowPath in Telegram with the button below.\n"
            "To link an existing website account, open Profile on the site "
            "and tap Connect Telegram."
        ),
        "welcome": (
            "Welcome to GlowPath. Open the app to set up your tracker — "
            "no website needed."
        ),
        "continue_onboarding": "Finish setup in the app to start tracking.",
        "open_app": "Open App",
        "log_mood": "Log mood",
        "log_prompt": "Log your mood in GlowPath.",
        "wizard_retired": "Mood is logged in the app now. Tap the button to open it.",
        "mini_app_not_configured": "The GlowPath app is not configured on this bot yet.",
        "linked_ok": (
            "Telegram is linked to your GlowPath account.\n"
            "Open the app anytime, or wait for reminders in this chat."
        ),
        "link_failed": "Could not link account: {detail}",
        "unlinked_ok": "Telegram has been unlinked from GlowPath.",
        "unlink_failed": "Could not unlink: {detail}",
        "not_linked": "Open GlowPath with the button below to get started.",
        "choose_score": "How are you feeling?",
        "choose_tags": "Tags — {group}\nTap to toggle, then Next.",
        "choose_frequent_tags": "Often this week\nTap to toggle, then Next.",
        "choose_goals": "Any goals for this entry?\nTap to toggle, then Next or Skip.",
        "note_prompt": (
            "Add content for this entry — you can combine them:\n"
            "• text note\n"
            "• voice message (one)\n"
            "• photos (up to 5)\n\n"
            "When finished, tap Next. Or Skip to leave this empty.\n"
            "/cancel aborts."
        ),
        "note_status": "Added so far: {parts}\nSend more, or tap Next.",
        "confirm": "Save this entry?\n\n{summary}",
        "saved": "Saved: {summary}",
        "cancelled": "Cancelled. Nothing was saved.",
        "nothing_to_cancel": "Nothing to cancel.",
        "skip": "Skip",
        "next": "Next",
        "confirm_yes": "Save",
        "confirm_no": "Cancel",
        "error": "Something went wrong: {detail}",
        "session_expired": "This check-in expired. Open the app to log your mood.",
        "voice_attached": "Voice note attached (replaces previous voice if any).",
        "note_saved_step": "Text note saved (you can still add voice or photos).",
        "photo_attached": "Photo added ({count}/{max}).",
        "photo_limit": "Photo limit reached (max {max}). Tap Next to continue.",
        "part_note": "text",
        "part_voice": "voice",
        "part_photos": "photos ×{count}",
    },
    "ru": {
        "help": (
            "Бот GlowPath\n\n"
            "Откройте приложение из меню или кнопкой ниже. Новые пользователи "
            "настраивают трекер в приложении — сайт не обязателен.\n\n"
            "Команды:\n"
            "/log — записать настроение в приложении\n"
            "/start <код> — привязать аккаунт с сайта\n"
            "/unlink — отвязать Telegram\n"
            "/help — эта справка"
        ),
        "already_linked": (
            "Telegram уже привязан к GlowPath.\n"
            "Откройте приложение, чтобы отметиться."
        ),
        "need_link": (
            "Откройте GlowPath кнопкой ниже.\n"
            "Чтобы связать уже существующий аккаунт с сайта, "
            "откройте профиль и нажмите «Подключить Telegram»."
        ),
        "welcome": (
            "Добро пожаловать в GlowPath. Откройте приложение, чтобы настроить "
            "трекер — сайт не нужен."
        ),
        "continue_onboarding": "Завершите настройку в приложении, чтобы начать.",
        "open_app": "Открыть приложение",
        "log_mood": "Записать настроение",
        "log_prompt": "Запиши настроение в GlowPath.",
        "wizard_retired": (
            "Настроение теперь отмечается в приложении. Нажмите кнопку, чтобы открыть."
        ),
        "mini_app_not_configured": "Приложение GlowPath на этом боте ещё не настроено.",
        "linked_ok": (
            "Telegram привязан к аккаунту GlowPath.\n"
            "Открывайте приложение в любой момент или ждите напоминания в этом чате."
        ),
        "link_failed": "Не удалось привязать: {detail}",
        "unlinked_ok": "Telegram отвязан от GlowPath.",
        "unlink_failed": "Не удалось отвязать: {detail}",
        "not_linked": "Откройте GlowPath кнопкой ниже, чтобы начать.",
        "choose_score": "Как вы себя чувствуете?",
        "choose_tags": "Теги — {group}\nНажимайте, чтобы выбрать, затем «Далее».",
        "choose_frequent_tags": "Часто за неделю\nНажимайте, чтобы выбрать, затем «Далее».",
        "choose_goals": "Цели для этой записи?\nВыберите, затем «Далее» или «Пропустить».",
        "note_prompt": (
            "Добавьте контент — можно комбинировать:\n"
            "• текстовую заметку\n"
            "• голосовое (одно)\n"
            "• фото (до 5)\n\n"
            "Когда закончите — «Далее». «Пропустить» — без контента.\n"
            "Отмена: /cancel."
        ),
        "note_status": "Уже добавлено: {parts}\nМожно добавить ещё или нажмите «Далее».",
        "confirm": "Сохранить запись?\n\n{summary}",
        "saved": "Сохранено: {summary}",
        "cancelled": "Отменено. Ничего не сохранено.",
        "nothing_to_cancel": "Нечего отменять.",
        "skip": "Пропустить",
        "next": "Далее",
        "confirm_yes": "Сохранить",
        "confirm_no": "Отмена",
        "error": "Ошибка: {detail}",
        "session_expired": "Сессия истекла. Откройте приложение, чтобы записаться.",
        "voice_attached": "Голосовое прикреплено (заменит предыдущее, если было).",
        "note_saved_step": "Текст сохранён (можно ещё добавить голос или фото).",
        "photo_attached": "Фото добавлено ({count}/{max}).",
        "photo_limit": "Лимит фото ({max}). Нажмите «Далее».",
        "part_note": "текст",
        "part_voice": "голос",
        "part_photos": "фото ×{count}",
    },
}

MESSAGES: dict[str, dict[str, str]] = {
    lang: {**base, **COMPANION_MESSAGES.get(lang, {})}
    for lang, base in _BASE_MESSAGES.items()
}


def normalize_bot_locale(locale: str | None) -> str:
    if not locale:
        return "en"
    primary = locale.split("-", 1)[0].strip().lower()
    return primary if primary in MESSAGES else "en"


def t(locale: str | None, key: str, **kwargs: Any) -> str:
    lang = normalize_bot_locale(locale)
    template = MESSAGES.get(lang, MESSAGES["en"]).get(key) or MESSAGES["en"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def companion_t(
    locale: str | None,
    base: str,
    timezone: str | None,
    *,
    variants: int = 3,
    **kwargs: Any,
) -> str:
    key = companion_key(base, timezone, variants=variants)
    lang = normalize_bot_locale(locale)
    template = MESSAGES.get(lang, MESSAGES["en"]).get(key) or MESSAGES["en"].get(key)
    if template is None:
        return t(locale, base, **kwargs)
    if kwargs:
        return template.format(**kwargs)
    return template
