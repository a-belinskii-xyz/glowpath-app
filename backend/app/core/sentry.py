from __future__ import annotations

import logging
from typing import Any, Literal

import sentry_sdk

from app.config import settings

logger = logging.getLogger(__name__)

# Render probes /health every few seconds; tracing those only burns quota.
_UNTRACED_TRANSACTIONS = frozenset({"/health"})

SentryStatus = Literal["off", "on", "failed"]
_status: SentryStatus = "off"


def sentry_status() -> SentryStatus:
    """Shown in /health so a silently disabled Sentry is visible."""
    return _status


def _traces_sampler(context: dict[str, Any]) -> float:
    parent_sampled = context.get("parent_sampled")
    if parent_sampled is not None:
        return float(parent_sampled)
    name = context.get("transaction_context", {}).get("name", "")
    if name in _UNTRACED_TRANSACTIONS:
        return 0.0
    return settings.sentry_traces_sample_rate


def init_sentry() -> None:
    """Start Sentry reporting. No-op without SENTRY_DSN."""
    global _status
    if not settings.sentry_dsn:
        return
    # Settings already rejects malformed DSNs; this guards against SDK bugs so
    # telemetry never takes the service down.
    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            release=settings.sentry_release or None,
            # Diary entries are personal health data: keep request bodies, IPs,
            # cookies, auth headers and frame locals out of events.
            send_default_pii=False,
            max_request_body_size="never",
            include_local_variables=False,
            traces_sampler=_traces_sampler,
            enable_logs=True,
        )
    except Exception:
        _status = "failed"
        logger.exception("Sentry init failed; running without it")
    else:
        _status = "on"
