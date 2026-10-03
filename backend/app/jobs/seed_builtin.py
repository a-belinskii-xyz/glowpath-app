"""Add built-in content a fresh database lacks: search tags and catalog achievements.

Runs on every API start (``docker-entrypoint.sh``), after migrations::

    python -m app.jobs.seed_builtin

Only adds what is missing by slug: achievements staff edited or archived stay as they
are, and rewards that point at packs this database doesn't have are dropped.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.achievement import Achievement
from app.services.achievements.seed import seed_achievements
from app.services.marketplace_seed import seed_default_search_tags

logger = logging.getLogger(__name__)


def seed_builtin_content(db: Session) -> list[Achievement]:
    """Returns the achievements it added."""
    seed_default_search_tags(db)
    return seed_achievements(db, only_missing=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with SessionLocal() as db:
        added = [achievement.slug for achievement in seed_builtin_content(db)]
        db.commit()
    if added:
        logger.info("Added built-in achievements: %s", ", ".join(added))


if __name__ == "__main__":
    main()
