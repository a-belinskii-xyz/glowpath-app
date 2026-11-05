from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlsplit

import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

from bot.config import settings

if TYPE_CHECKING:
    from sentry_sdk._types import Hint, Log

logger = logging.getLogger(__name__)

# Render probes /health and the SPA keep-alive (useKeepServerAwake) pings
# /v1/health; tracing those only burns quota.
_UNTRACED_TRANSACTIONS = frozenset({"/health", "/v1/health"})

SentryStatus = Literal["off", "on", "failed"]
_status: SentryStatus = "off"


def sentry_status() -> SentryStatus:
    """Shown in /health so a silently disabled Sentry is visible."""
    return _status


def _request_path(context: dict[str, Any]) -> str:
    # At sampling time the transaction name is the full URL
    # (http://host/health), so prefer the ASGI path.
    path = context.get("asgi_scope", {}).get("path")
    if isinstance(path, str):
        return path
    name = context.get("transaction_context", {}).get("name", "")
    return urlsplit(str(name)).path


def _traces_sampler(context: dict[str, Any]) -> float:
    # Checked before parent_sampled: the browser SDK's sampling decision would
    # otherwise pull keep-alive pings into traces.
    if _request_path(context) in _UNTRACED_TRANSACTIONS:
        return 0.0
    parent_sampled = context.get("parent_sampled")
    if parent_sampled is not None:
        return float(parent_sampled)
    return settings.sentry_traces_sample_rate


# Access log lines carry client IPs and full URLs with one-time tokens
# (?token=, OAuth ?code=).
_PRIVATE_LOGGERS = frozenset({"uvicorn.access"})


def _before_send_log(log: Log, _hint: Hint) -> Log | None:
    # Logs are off (no enable_logs); this keeps access lines out if they are
    # ever turned on. ignore_logger() alone does not cover Sentry Logs.
    if log["attributes"].get("logger.name") in _PRIVATE_LOGGERS:
        return None
    return log


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
            # Updates carry users' chat messages: keep bodies, IPs, headers
            # (webhook secret) and frame locals out of events.
            send_default_pii=False,
            max_request_body_size="never",
            include_local_variables=False,
            traces_sampler=_traces_sampler,
            before_send_log=_before_send_log,
        )
        # No error events or breadcrumbs from access lines either.
        for name in _PRIVATE_LOGGERS:
            ignore_logger(name)
    except Exception:
        _status = "failed"
        logger.exception("Sentry init failed; running without it")
    else:
        _status = "on"
