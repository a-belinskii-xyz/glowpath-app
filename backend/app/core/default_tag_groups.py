"""Default tag groups copied to each user on registration (stage 2)."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels


@dataclass(frozen=True, slots=True)
class DefaultTag:
    slug: str
    labels: LocaleLabels


@dataclass(frozen=True, slots=True)
class DefaultTagGroup:
    slug: str
    labels: LocaleLabels
    tags: tuple[DefaultTag, ...]


DEFAULT_TAG_GROUPS: tuple[DefaultTagGroup, ...] = (
    DefaultTagGroup(
        slug="weather",
        labels={"en": "Weather", "ru": "Погода"},
        tags=(
            DefaultTag("sunny", {"en": "Sunny", "ru": "Солнечно"}),
            DefaultTag("cloudy", {"en": "Cloudy", "ru": "Облачно"}),
            DefaultTag("rain", {"en": "Rain", "ru": "Дождь"}),
            DefaultTag("thunderstorm", {"en": "Thunderstorm", "ru": "Гроза"}),
        ),
    ),
    DefaultTagGroup(
        slug="sleep_quality",
        labels={"en": "Sleep quality", "ru": "Качество сна"},
        tags=(
            DefaultTag("slept_well", {"en": "Slept well", "ru": "Хорошо поспал"}),
            DefaultTag("average_sleep", {"en": "Average sleep", "ru": "Средний сон"}),
            DefaultTag("slept_poorly", {"en": "Slept poorly", "ru": "Плохо спал"}),
        ),
    ),
    DefaultTagGroup(
        slug="mood",
        labels={"en": "Mood", "ru": "Настроение"},
        tags=(
            DefaultTag("joy", {"en": "Joy", "ru": "Радость"}),
            DefaultTag("anxiety", {"en": "Anxiety", "ru": "Тревога"}),
            DefaultTag("fatigue", {"en": "Fatigue", "ru": "Усталость"}),
            DefaultTag("calm", {"en": "Calm", "ru": "Спокойствие"}),
        ),
    ),
    DefaultTagGroup(
        slug="activity",
        labels={"en": "Activity", "ru": "Активность"},
        tags=(
            DefaultTag("work", {"en": "Work", "ru": "Работа"}),
            DefaultTag("sport", {"en": "Sport", "ru": "Спорт"}),
            DefaultTag("social", {"en": "Socializing", "ru": "Общение"}),
            DefaultTag("rest", {"en": "Rest", "ru": "Отдых"}),
        ),
    ),
)
