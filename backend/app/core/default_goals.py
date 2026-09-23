"""Default goals copied to each user on registration (BASE pack)."""

from dataclasses import dataclass

from app.core.i18n import LocaleLabels
from app.core.onboarding_packs import get_base_pack

DEFAULT_GOAL_COLOR = "#60a5fa"
DEFAULT_GOAL_ICON = "🎯"


@dataclass(frozen=True, slots=True)
class DefaultGoal:
    slug: str
    labels: LocaleLabels
    times_per_week: int
    color: str = DEFAULT_GOAL_COLOR
    icon: str = DEFAULT_GOAL_ICON


def _load_default_goals() -> tuple[DefaultGoal, ...]:
    base = get_base_pack()
    return tuple(
        DefaultGoal(
            slug=goal.slug,
            labels=dict(goal.labels),
            times_per_week=goal.times_per_week,
            color=goal.color,
            icon=goal.icon,
        )
        for goal in sorted(base.goals, key=lambda item: (item.sort_order, item.slug))
    )


DEFAULT_GOALS: tuple[DefaultGoal, ...] = _load_default_goals()
