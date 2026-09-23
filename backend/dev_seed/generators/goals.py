from __future__ import annotations

import uuid
from datetime import date

from app.config import settings
from app.core.default_goals import DEFAULT_GOALS
from app.models.goal import Goal
from sqlalchemy import select
from sqlalchemy.orm import Session

from dev_seed.personas import Persona
from dev_seed.rng import SeededRNG


def provision_goals(
    db: Session,
    *,
    user_id: uuid.UUID,
    persona: Persona,
    rng: SeededRNG,
    starts_on: date,
) -> list[Goal]:
    """Default catalog + persona custom goals covering the full seed history window."""
    visible_limit = settings.entry_visible_goal_limit
    stats_limit = settings.stats_visible_goal_limit

    for order, default_goal in enumerate(DEFAULT_GOALS):
        db.add(
            Goal(
                id=rng.uuid("goal", f"{persona.key}:default:{default_goal.slug}"),
                user_id=user_id,
                slug=default_goal.slug,
                labels=dict(default_goal.labels),
                times_per_week=default_goal.times_per_week,
                starts_on=starts_on,
                sort_order=order,
                show_on_entry=order < visible_limit,
                show_in_stats=order < stats_limit,
            )
        )

    base_order = len(DEFAULT_GOALS)
    for offset, custom_goal in enumerate(persona.custom_goals):
        order = base_order + offset
        db.add(
            Goal(
                id=rng.uuid("goal", f"{persona.key}:custom:{custom_goal.slug}"),
                user_id=user_id,
                slug=custom_goal.slug,
                labels=dict(custom_goal.labels),
                times_per_week=custom_goal.times_per_week,
                starts_on=starts_on,
                sort_order=order,
                show_on_entry=False,
                show_in_stats=order < stats_limit,
            )
        )

    db.flush()
    return list(
        db.scalars(select(Goal).where(Goal.user_id == user_id).order_by(Goal.sort_order)).all()
    )
