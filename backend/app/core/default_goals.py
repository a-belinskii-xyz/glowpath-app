"""Default goals copied to each user on registration."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels


@dataclass(frozen=True, slots=True)
class DefaultGoal:
    slug: str
    labels: LocaleLabels
    times_per_week: int


DEFAULT_GOALS: tuple[DefaultGoal, ...] = (
    DefaultGoal(
        slug="early_rise",
        labels={"en": "Early rise", "ru": "Ранний подъём"},
        times_per_week=7,
    ),
    DefaultGoal(
        slug="min_screen_time",
        labels={"en": "Min screen time", "ru": "Меньше экрана"},
        times_per_week=5,
    ),
    DefaultGoal(
        slug="exercise",
        labels={"en": "Exercise", "ru": "Тренировка"},
        times_per_week=3,
    ),
)
