"""Reminder worker: poll and send due mood / goal notifications.

Run once (e.g. cron)::

    python -m app.jobs.reminders --once

Run as a long-lived worker (Docker Compose ``reminders`` service)::

    python -m app.jobs.reminders

On hosts without a background worker (Render free plan), an external
scheduler calls ``POST /v1/internal/reminders/tick`` instead.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from app.config import settings
from app.db.session import SessionLocal
from app.services.notifications.factory import build_notification_dispatcher
from app.services.notifications.tick import run_reminder_tick

logger = logging.getLogger(__name__)


def run_once() -> int:
    dispatcher = build_notification_dispatcher()
    with SessionLocal() as db:
        result = run_reminder_tick(db, dispatcher)
    return 0 if not result.stats.errors else 1


def run_loop() -> None:
    interval = settings.notifications_poll_interval_seconds
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("reminder run failed")
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send due GlowPath reminder notifications")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process due reminders once and exit (for cron)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.once:
        return run_once()
    run_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
