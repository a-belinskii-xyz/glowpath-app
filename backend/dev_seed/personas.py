from __future__ import annotations

from dataclasses import dataclass

from dev_seed.config import SEED_EMAIL_DOMAIN
from dev_seed.logging_styles import (
    CONSISTENT,
    IRREGULAR,
    ON_OFF_WEEKS,
    REFLECTIVE,
    SOCIAL_BURSTS,
    SPARSE,
    WEEKDAY_WORKER,
    WEEKEND_NATURE,
    LoggingStyle,
)


@dataclass(frozen=True, slots=True)
class CustomTag:
    slug: str
    labels: dict[str, str]


@dataclass(frozen=True, slots=True)
class CustomTagGroup:
    slug: str
    labels: dict[str, str]
    tags: tuple[CustomTag, ...]


@dataclass(frozen=True, slots=True)
class Persona:
    key: str
    display_name: str
    local_part: str
    timezone: str
    note_locale: str  # "ru" | "en"
    custom_groups: tuple[CustomTagGroup, ...]
    note_flavor: str  # flavor key for note pool selection
    logging: LoggingStyle

    @property
    def email(self) -> str:
        return f"{self.local_part}@{SEED_EMAIL_DOMAIN}"


PERSONAS: tuple[Persona, ...] = (
    Persona(
        key="alice",
        display_name="Alice Novak",
        local_part="alice",
        timezone="Europe/Warsaw",
        note_locale="en",
        note_flavor="active",
        logging=CONSISTENT,
        custom_groups=(
            CustomTagGroup(
                slug="hobbies",
                labels={"en": "Hobbies", "ru": "Хобби"},
                tags=(
                    CustomTag("running", {"en": "Running", "ru": "Бег"}),
                    CustomTag("reading", {"en": "Reading", "ru": "Чтение"}),
                    CustomTag("cooking", {"en": "Cooking", "ru": "Готовка"}),
                ),
            ),
            CustomTagGroup(
                slug="people",
                labels={"en": "People", "ru": "Люди"},
                tags=(
                    CustomTag("family", {"en": "Family", "ru": "Семья"}),
                    CustomTag("friends", {"en": "Friends", "ru": "Друзья"}),
                    CustomTag("colleagues", {"en": "Colleagues", "ru": "Коллеги"}),
                ),
            ),
        ),
    ),
    Persona(
        key="bob",
        display_name="Bob Kowalski",
        local_part="bob",
        timezone="Europe/Minsk",
        note_locale="ru",
        note_flavor="calm",
        logging=SPARSE,
        custom_groups=(
            CustomTagGroup(
                slug="location",
                labels={"en": "Place", "ru": "Место"},
                tags=(
                    CustomTag("home", {"en": "Home", "ru": "Дом"}),
                    CustomTag("office", {"en": "Office", "ru": "Офис"}),
                    CustomTag("cafe", {"en": "Cafe", "ru": "Кафе"}),
                    CustomTag("outdoors", {"en": "Outdoors", "ru": "На улице"}),
                ),
            ),
        ),
    ),
    Persona(
        key="carol",
        display_name="Carol Berg",
        local_part="carol",
        timezone="Europe/Berlin",
        note_locale="en",
        note_flavor="work",
        logging=WEEKDAY_WORKER,
        custom_groups=(
            CustomTagGroup(
                slug="energy",
                labels={"en": "Energy", "ru": "Энергия"},
                tags=(
                    CustomTag("high", {"en": "High", "ru": "Высокая"}),
                    CustomTag("medium", {"en": "Medium", "ru": "Средняя"}),
                    CustomTag("low", {"en": "Low", "ru": "Низкая"}),
                ),
            ),
            CustomTagGroup(
                slug="focus",
                labels={"en": "Focus", "ru": "Фокус"},
                tags=(
                    CustomTag("deep_work", {"en": "Deep work", "ru": "Глубокая работа"}),
                    CustomTag("meetings", {"en": "Meetings", "ru": "Встречи"}),
                    CustomTag("distracted", {"en": "Distracted", "ru": "Отвлечённость"}),
                ),
            ),
        ),
    ),
    Persona(
        key="diana",
        display_name="Diana Petrova",
        local_part="diana",
        timezone="Europe/Moscow",
        note_locale="ru",
        note_flavor="social",
        logging=SOCIAL_BURSTS,
        custom_groups=(
            CustomTagGroup(
                slug="food",
                labels={"en": "Food", "ru": "Еда"},
                tags=(
                    CustomTag("healthy", {"en": "Healthy", "ru": "Здоровая"}),
                    CustomTag("comfort", {"en": "Comfort food", "ru": "Комфорт-еда"}),
                    CustomTag("skipped", {"en": "Skipped meal", "ru": "Пропуск еды"}),
                ),
            ),
        ),
    ),
    Persona(
        key="evan",
        display_name="Evan Mills",
        local_part="evan",
        timezone="Europe/London",
        note_locale="en",
        note_flavor="reflective",
        logging=REFLECTIVE,
        custom_groups=(
            CustomTagGroup(
                slug="health",
                labels={"en": "Health", "ru": "Здоровье"},
                tags=(
                    CustomTag("workout", {"en": "Workout", "ru": "Тренировка"}),
                    CustomTag("stretch", {"en": "Stretching", "ru": "Растяжка"}),
                    CustomTag("headache", {"en": "Headache", "ru": "Головная боль"}),
                    CustomTag("allergy", {"en": "Allergy", "ru": "Аллергия"}),
                ),
            ),
            CustomTagGroup(
                slug="media",
                labels={"en": "Media", "ru": "Медиа"},
                tags=(
                    CustomTag("podcast", {"en": "Podcast", "ru": "Подкаст"}),
                    CustomTag("music", {"en": "Music", "ru": "Музыка"}),
                    CustomTag("news", {"en": "News", "ru": "Новости"}),
                ),
            ),
        ),
    ),
    Persona(
        key="fiona",
        display_name="Fiona Lee",
        local_part="fiona",
        timezone="Asia/Singapore",
        note_locale="en",
        note_flavor="active",
        logging=IRREGULAR,
        custom_groups=(
            CustomTagGroup(
                slug="travel",
                labels={"en": "Travel", "ru": "Поездки"},
                tags=(
                    CustomTag("commute", {"en": "Commute", "ru": "Дорога"}),
                    CustomTag("weekend_trip", {"en": "Weekend trip", "ru": "Выходные"}),
                ),
            ),
        ),
    ),
    Persona(
        key="george",
        display_name="Georgy Ivanov",
        local_part="george",
        timezone="Europe/Minsk",
        note_locale="ru",
        note_flavor="work",
        logging=ON_OFF_WEEKS,
        custom_groups=(
            CustomTagGroup(
                slug="projects",
                labels={"en": "Projects", "ru": "Проекты"},
                tags=(
                    CustomTag("side_project", {"en": "Side project", "ru": "Сайд-проект"}),
                    CustomTag("deadline", {"en": "Deadline", "ru": "Дедлайн"}),
                    CustomTag("learning", {"en": "Learning", "ru": "Обучение"}),
                ),
            ),
        ),
    ),
    Persona(
        key="helen",
        display_name="Helen Sjöberg",
        local_part="helen",
        timezone="Europe/Stockholm",
        note_locale="en",
        note_flavor="calm",
        logging=WEEKEND_NATURE,
        custom_groups=(
            CustomTagGroup(
                slug="nature",
                labels={"en": "Nature", "ru": "Природа"},
                tags=(
                    CustomTag("forest", {"en": "Forest", "ru": "Лес"}),
                    CustomTag("lake", {"en": "Lake", "ru": "Озеро"}),
                    CustomTag("rainy_walk", {"en": "Rainy walk", "ru": "Прогулка под дождём"}),
                ),
            ),
        ),
    ),
)


def seed_emails(*, count: int | None = None) -> list[str]:
    personas = PERSONAS if count is None else PERSONAS[:count]
    return [p.email for p in personas]


def personas_for_count(count: int) -> list[Persona]:
    if count < 1:
        raise ValueError("--users must be >= 1")
    if count > len(PERSONAS):
        raise ValueError(f"--users cannot exceed {len(PERSONAS)} (available personas)")
    return list(PERSONAS[:count])
