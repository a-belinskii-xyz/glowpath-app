"""Time-of-day companion copy (user timezone).

Finer bins than insight analytics: late night, morning, midday, afternoon,
evening, night. Used for daily reminders and shared conceptually with the
frontend / Telegram bot.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.i18n import DEFAULT_LOCALE, LocaleLabels, normalize_locale


class CompanionDaypart(StrEnum):
    LATE_NIGHT = "lateNight"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


def companion_daypart_for_hour(hour: int) -> CompanionDaypart:
    """Map a local hour (0–23) to a companion daypart."""
    normalized = 0 if hour == 24 else hour
    if normalized < 0 or normalized > 23:
        raise ValueError(f"hour out of range: {hour}")
    if normalized < 5:
        return CompanionDaypart.LATE_NIGHT
    if normalized < 11:
        return CompanionDaypart.MORNING
    if normalized < 14:
        return CompanionDaypart.MIDDAY
    if normalized < 17:
        return CompanionDaypart.AFTERNOON
    if normalized < 21:
        return CompanionDaypart.EVENING
    return CompanionDaypart.NIGHT


def pick_companion_variant(seed: str, count: int) -> int:
    if count <= 1:
        return 0
    hash_value = 2166136261
    for char in seed:
        hash_value ^= ord(char)
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return hash_value % count


class CompanionStyle(StrEnum):
    """How the companion talks. One style for now; others add their own phrase sets."""

    DEFAULT = "default"


_DAILY_REMINDER_SUBJECT: dict[CompanionStyle, dict[CompanionDaypart, LocaleLabels]] = {
    CompanionStyle.DEFAULT: {
        CompanionDaypart.LATE_NIGHT: {
            "en": "Still up? Log your mood",
            "ru": "Ещё не спишь? Запиши настроение",
        },
        CompanionDaypart.MORNING: {
            "en": "Good morning — log your mood",
            "ru": "Доброе утро — запиши настроение",
        },
        CompanionDaypart.MIDDAY: {
            "en": "Midday — log your mood",
            "ru": "Середина дня — запиши настроение",
        },
        CompanionDaypart.AFTERNOON: {
            "en": "Afternoon — log your mood",
            "ru": "День идёт — запиши настроение",
        },
        CompanionDaypart.EVENING: {
            "en": "Evening — log your mood",
            "ru": "Вечер — запиши настроение",
        },
        CompanionDaypart.NIGHT: {
            "en": "Tonight — log your mood",
            "ru": "На вечер — запиши настроение",
        },
    },
}

# Several phrasings per daypart; one is picked per person and day (see daily_reminder_intro).
_DAILY_REMINDER_INTRO: dict[CompanionStyle, dict[CompanionDaypart, tuple[LocaleLabels, ...]]] = {
    CompanionStyle.DEFAULT: {
        CompanionDaypart.LATE_NIGHT: (
            {
                "en": "Still awake? A few words are enough, if you like.",
                "ru": "Ещё не спишь? Можно просто оставить пару слов.",
            },
            {
                "en": "It’s quiet out. No rush, a short note will do.",
                "ru": "Тихо вокруг. Никуда не спеши, хватит короткой заметки.",
            },
            {
                "en": "Late hour. How are you feeling right now?",
                "ru": "Поздний час. Как ты сейчас?",
            },
        ),
        CompanionDaypart.MORNING: (
            {
                "en": "Good morning. How are you today?",
                "ru": "Доброе утро. Как ты?",
            },
            {
                "en": "New day. How did you wake up?",
                "ru": "Новый день. Какое настроение с утра?",
            },
            {
                "en": "Morning. A quick check-in before the day gets busy?",
                "ru": "Утро. Отметишься, пока день не закрутил?",
            },
        ),
        CompanionDaypart.MIDDAY: (
            {
                "en": "How’s the day going so far? A short note is plenty.",
                "ru": "Как день идёт? Короткой записи вполне хватит.",
            },
            {
                "en": "Middle of the day. How are you holding up?",
                "ru": "Середина дня. Как ты там?",
            },
            {
                "en": "Around lunch. Want to jot down how you feel?",
                "ru": "Время обеда. Запишешь, как настроение?",
            },
        ),
        CompanionDaypart.AFTERNOON: (
            {
                "en": "How’s the afternoon going? A short note is plenty.",
                "ru": "Как там день? Короткой записи вполне хватит.",
            },
            {
                "en": "Afternoon already. How are you feeling?",
                "ru": "Уже вторая половина дня. Как ты?",
            },
            {
                "en": "A short pause for yourself? One line is enough.",
                "ru": "Маленькая пауза для себя? Хватит одной строчки.",
            },
        ),
        CompanionDaypart.EVENING: (
            {
                "en": "Evening. Want to leave a few words about today?",
                "ru": "Вечер. Хочешь оставить пару слов про сегодня?",
            },
            {
                "en": "It’s evening already. How are you?",
                "ru": "Уже вечер. Как ты?",
            },
            {
                "en": "The day is slowing down. How did it go?",
                "ru": "День затихает. Как он прошёл?",
            },
        ),
        CompanionDaypart.NIGHT: (
            {
                "en": "Almost done with the day. A last note, if you want.",
                "ru": "День почти кончился. Последняя заметка — если хочется.",
            },
            {
                "en": "Before bed: how was today?",
                "ru": "Перед сном: каким был сегодняшний день?",
            },
            {
                "en": "Time to wind down. A few words about today?",
                "ru": "Пора выдохнуть. Пару слов про сегодня?",
            },
        ),
    },
}


def daily_reminder_subject(
    *,
    hour: int,
    locale: str = DEFAULT_LOCALE,
    style: CompanionStyle = CompanionStyle.DEFAULT,
) -> str:
    part = companion_daypart_for_hour(hour)
    phrases = _DAILY_REMINDER_SUBJECT.get(style) or _DAILY_REMINDER_SUBJECT[CompanionStyle.DEFAULT]
    return _label(phrases[part], locale)


def daily_reminder_intro(
    *,
    hour: int,
    locale: str = DEFAULT_LOCALE,
    seed: str = "",
    style: CompanionStyle = CompanionStyle.DEFAULT,
) -> str:
    """Pick one phrasing for the daypart; the same *seed* always gives the same one."""
    part = companion_daypart_for_hour(hour)
    phrases = _DAILY_REMINDER_INTRO.get(style) or _DAILY_REMINDER_INTRO[CompanionStyle.DEFAULT]
    variants = phrases[part]
    index = pick_companion_variant(f"{seed}:intro:{part.value}", len(variants)) if seed else 0
    return _label(variants[index], locale)


def _label(labels: LocaleLabels, locale: str) -> str:
    normalized = normalize_locale(locale)
    if normalized in labels:
        return labels[normalized]
    return labels[DEFAULT_LOCALE]
