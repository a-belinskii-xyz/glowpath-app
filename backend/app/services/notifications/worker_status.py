"""Liveness of the reminders worker, based on its last heartbeat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.core.i18n import DEFAULT_LOCALE, resolve_label
from app.models.system_worker_heartbeat import SystemWorkerHeartbeat
from app.schemas.notification_settings import (
    NotificationStatusCode,
    NotificationSystemStatus,
    WorkerLiveness,
)

REMINDERS_WORKER_NAME = "reminders"

_STATUS_MESSAGES: dict[NotificationStatusCode, dict[str, str]] = {
    NotificationStatusCode.OK: {
        "en": "Notifications are running.",
        "ru": "Уведомления работают.",
    },
    NotificationStatusCode.DISABLED_STAGE_TESTING: {
        "en": "Notifications are temporarily off while the app is in closed testing.",
        "ru": "Уведомления временно отключены: сервис находится на этапе закрытого тестирования.",
    },
    NotificationStatusCode.WORKER_OFFLINE: {
        "en": "The notification sender is temporarily unavailable. Reminders may be delayed.",
        "ru": (
            "Сервис отправки уведомлений временно недоступен — уже разбираемся. "
            "Напоминания могут задерживаться или не приходить."
        ),
    },
}


def record_heartbeat(
    db: Session,
    *,
    worker_name: str = REMINDERS_WORKER_NAME,
    meta: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> None:
    instant = at if at is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    payload = meta if meta is not None else {}
    stmt = insert(SystemWorkerHeartbeat).values(
        worker_name=worker_name,
        last_heartbeat_at=instant,
        meta=payload,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[SystemWorkerHeartbeat.worker_name],
        set_={
            "last_heartbeat_at": instant,
            "meta": payload,
        },
    )
    db.execute(stmt)
    db.commit()


def worker_liveness(
    last_heartbeat_at: datetime | None,
    *,
    now: datetime | None = None,
    poll_interval_seconds: int | None = None,
) -> WorkerLiveness:
    if last_heartbeat_at is None:
        return WorkerLiveness.OFFLINE
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    seen = last_heartbeat_at
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    age_seconds = (instant - seen).total_seconds()
    interval = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else settings.notifications_poll_interval_seconds
    )
    if age_seconds <= interval:
        return WorkerLiveness.HEALTHY
    if age_seconds <= interval * 2.5:
        return WorkerLiveness.DEGRADED
    return WorkerLiveness.OFFLINE


def system_status(
    db: Session,
    *,
    locale: str = DEFAULT_LOCALE,
    now: datetime | None = None,
) -> NotificationSystemStatus:
    row = db.get(SystemWorkerHeartbeat, REMINDERS_WORKER_NAME)
    liveness = worker_liveness(None if row is None else row.last_heartbeat_at, now=now)
    feature_on = settings.feature_notifications_enabled
    if not feature_on:
        code = NotificationStatusCode.DISABLED_STAGE_TESTING
    elif liveness is WorkerLiveness.OFFLINE:
        code = NotificationStatusCode.WORKER_OFFLINE
    else:
        code = NotificationStatusCode.OK
    return NotificationSystemStatus(
        feature_enabled=feature_on,
        worker_status=liveness,
        status_code=code,
        message=resolve_label(_STATUS_MESSAGES[code], locale),
    )
