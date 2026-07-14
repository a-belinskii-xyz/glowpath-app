"""Default note templates copied to each user on registration."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels


@dataclass(frozen=True, slots=True)
class DefaultNoteTemplate:
    slug: str
    labels: LocaleLabels
    bodies: LocaleLabels


DEFAULT_NOTE_TEMPLATES: tuple[DefaultNoteTemplate, ...] = (
    DefaultNoteTemplate(
        slug="daily_reflection",
        labels={"en": "Daily reflection", "ru": "Дневная рефлексия"},
        bodies={
            "en": ("## What I did\n\n\n## What got in the way\n\n\n## What I'll do tomorrow\n\n"),
            "ru": ("## Что я делал\n\n\n## Что мне мешало\n\n\n## Что я буду делать завтра\n\n"),
        },
    ),
    DefaultNoteTemplate(
        slug="gratitude",
        labels={"en": "Gratitude", "ru": "Благодарность"},
        bodies={
            "en": ("## Three things I'm grateful for\n\n1. \n2. \n3. \n"),
            "ru": ("## Три вещи, за которые я благодарен\n\n1. \n2. \n3. \n"),
        },
    ),
    DefaultNoteTemplate(
        slug="mood_check_in",
        labels={"en": "Mood check-in", "ru": "Чек-ин настроения"},
        bodies={
            "en": ("## How I feel\n\n\n## Why\n\n\n## What would help\n\n"),
            "ru": ("## Как я себя чувствую\n\n\n## Почему\n\n\n## Что бы помогло\n\n"),
        },
    ),
)
