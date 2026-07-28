"""Default tag groups copied to each user on registration (stage 2)."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels

DEFAULT_TAG_COLOR = "#94a3b8"
DEFAULT_TAG_ICON_TYPE = "emoji"
DEFAULT_TAG_ICON = "🏷"


@dataclass(frozen=True, slots=True)
class DefaultTag:
    slug: str
    labels: LocaleLabels
    color: str = DEFAULT_TAG_COLOR
    icon: str = DEFAULT_TAG_ICON


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
            DefaultTag("sunny", {"en": "Sunny", "ru": "Солнечно"}, "#f59e0b", "☀️"),
            DefaultTag("cloudy", {"en": "Cloudy", "ru": "Облачно"}, "#94a3b8", "☁️"),
            DefaultTag("rain", {"en": "Rain", "ru": "Дождь"}, "#60a5fa", "🌧"),
            DefaultTag("thunderstorm", {"en": "Thunderstorm", "ru": "Гроза"}, "#6366f1", "⛈"),
        ),
    ),
    DefaultTagGroup(
        slug="sleep_quality",
        labels={"en": "Sleep quality", "ru": "Качество сна"},
        tags=(
            DefaultTag("slept_well", {"en": "Slept well", "ru": "Хорошо поспал"}, "#34d399", "😴"),
            DefaultTag(
                "average_sleep",
                {"en": "Average sleep", "ru": "Средний сон"},
                "#94a3b8",
                "😑",
            ),
            DefaultTag(
                "slept_poorly",
                {"en": "Slept poorly", "ru": "Плохо спал"},
                "#f87171",
                "😩",
            ),
        ),
    ),
    DefaultTagGroup(
        slug="mood",
        labels={"en": "Mood", "ru": "Настроение"},
        tags=(
            DefaultTag("joy", {"en": "Joy", "ru": "Радость"}, "#f59e0b", "😊"),
            DefaultTag("anxiety", {"en": "Anxiety", "ru": "Тревога"}, "#a78bfa", "😰"),
            DefaultTag("fatigue", {"en": "Fatigue", "ru": "Усталость"}, "#94a3b8", "😮‍💨"),
            DefaultTag("calm", {"en": "Calm", "ru": "Спокойствие"}, "#34d399", "😌"),
        ),
    ),
    DefaultTagGroup(
        slug="activity",
        labels={"en": "Activity", "ru": "Активность"},
        tags=(
            DefaultTag("work", {"en": "Work", "ru": "Работа"}, "#60a5fa", "💼"),
            DefaultTag("sport", {"en": "Sport", "ru": "Спорт"}, "#34d399", "🏃"),
            DefaultTag("social", {"en": "Socializing", "ru": "Общение"}, "#f472b6", "💬"),
            DefaultTag("rest", {"en": "Rest", "ru": "Отдых"}, "#a78bfa", "🛋"),
        ),
    ),
)

# Known seed / persona slugs → style (used by migration backfill).
KNOWN_TAG_STYLES: dict[str, tuple[str, str]] = {
    tag.slug: (tag.color, tag.icon) for group in DEFAULT_TAG_GROUPS for tag in group.tags
}
KNOWN_TAG_STYLES.update(
    {
        "running": ("#34d399", "🏃"),
        "reading": ("#60a5fa", "📖"),
        "cooking": ("#f59e0b", "🍳"),
        "family": ("#f472b6", "👨‍👩‍👧"),
        "friends": ("#60a5fa", "👥"),
        "colleagues": ("#94a3b8", "🧑‍💼"),
        "home": ("#f59e0b", "🏠"),
        "office": ("#60a5fa", "🏢"),
        "cafe": ("#d97706", "☕"),
        "outdoors": ("#34d399", "🌳"),
    }
)
