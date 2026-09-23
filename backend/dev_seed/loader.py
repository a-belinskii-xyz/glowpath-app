from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.db.session import SessionLocal
from app.services.storage import MinioStorage

from dev_seed.config import DEFAULT_PASSWORD
from dev_seed.generators.entries import create_entries_for_user
from dev_seed.generators.goals import provision_goals
from dev_seed.generators.tags import provision_tags
from dev_seed.generators.users import create_user
from dev_seed.personas import Persona, personas_for_count
from dev_seed.purge import purge_seed_users
from dev_seed.rng import SeededRNG


@dataclass(slots=True)
class SeedResult:
    seed: int
    users: list[Persona]
    entries: int
    attachments: int
    goals: int
    purged_users: int
    purged_objects: int


def run_seed(
    *,
    seed: int,
    user_count: int,
    days: int,
    entries_per_day_min: int | None = None,
    entries_per_day_max: int | None = None,
) -> SeedResult:
    if entries_per_day_min is not None or entries_per_day_max is not None:
        lo = entries_per_day_min if entries_per_day_min is not None else 1
        hi = entries_per_day_max if entries_per_day_max is not None else lo
        if lo < 1 or hi < lo:
            raise ValueError("Invalid entries-per-day range")

    personas = personas_for_count(user_count)
    rng = SeededRNG.create(seed)
    storage = MinioStorage()
    storage.ensure_bucket()

    with SessionLocal() as db:
        purged_users, purged_objects = purge_seed_users(db, user_count=None)
        db.commit()

        total_entries = 0
        total_attachments = 0
        total_goals = 0

        for persona in personas:
            user = create_user(db, persona=persona, rng=rng)
            tags = provision_tags(db, user_id=user.id, persona=persona, rng=rng)
            starts_on = datetime.now(ZoneInfo(persona.timezone)).date() - timedelta(days=days)
            goals = provision_goals(
                db,
                user_id=user.id,
                persona=persona,
                rng=rng,
                starts_on=starts_on,
            )
            entries, attachments = create_entries_for_user(
                db,
                user_id=user.id,
                persona=persona,
                tags=tags,
                goals=goals,
                rng=rng,
                days=days,
                entries_per_day_min=entries_per_day_min,
                entries_per_day_max=entries_per_day_max,
                storage=storage,
            )
            total_entries += entries
            total_attachments += attachments
            total_goals += len(goals)

        db.commit()

    return SeedResult(
        seed=seed,
        users=personas,
        entries=total_entries,
        attachments=total_attachments,
        goals=total_goals,
        purged_users=purged_users,
        purged_objects=purged_objects,
    )


def format_report(result: SeedResult) -> str:
    lines = [
        f"Seed complete (seed={result.seed})",
        f"  purged: {result.purged_users} users, {result.purged_objects} MinIO objects",
        f"  created: {len(result.users)} users, {result.entries} entries,"
        f" {result.attachments} attachments, {result.goals} goals",
        "",
        f"Login password for all seed users: {DEFAULT_PASSWORD}",
        "",
        f"{'Email':<30} {'Style':<14} {'Timezone':<18} Name",
        "-" * 78,
    ]
    for persona in result.users:
        lines.append(
            f"{persona.email:<30} {persona.logging.label:<14} "
            f"{persona.timezone:<18} {persona.display_name}"
        )
    return "\n".join(lines)
