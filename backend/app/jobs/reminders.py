"""Reminder worker: poll and send due mood / goal notifications.

Run once (e.g. cron)::

    python -m app.jobs.reminders --once

Run as a long-lived worker (Docker Compose ``reminders`` service)::

    python -m app.jobs.reminders
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from app.config import settings
from app.db.session import SessionLocal
from app.services.notifications.factory import build_notification_dispatcher
from app.services.notifications.reminders import process_due_reminders
from app.services.notifications.worker_status import record_heartbeat

logger = logging.getLogger(__name__)


def run_once() -> int:
    with SessionLocal() as db:
        record_heartbeat(db, meta={"phase": "tick"})

    if not settings.notifications_worker_enabled:
        logger.warning("NOTIFICATIONS_WORKER_ENABLED=false — worker idle until enabled")
        return 0
    if not settings.feature_notifications_enabled:
        logger.info("FEATURE_NOTIFICATIONS_ENABLED=false — sleeping without scanning users")
        return 0

    dispatcher = build_notification_dispatcher()
    with SessionLocal() as db:
        stats = process_due_reminders(db, dispatcher)
        record_heartbeat(
            db,
            meta={
                "phase": "done",
                "users_considered": stats.users_considered,
                "daily_mood_sent": stats.daily_mood_sent,
                "goal_reminders_sent": stats.goal_reminders_sent,
                "skipped": stats.skipped,
                "errors": len(stats.errors),
            },
        )
    logger.info(
        "reminders done: considered=%s daily=%s goals=%s skipped=%s errors=%s",
        stats.users_considered,
        stats.daily_mood_sent,
        stats.goal_reminders_sent,
        stats.skipped,
        len(stats.errors),
    )
    for error in stats.errors:
        logger.warning("reminder error: %s", error)
    return 0 if not stats.errors else 1


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
