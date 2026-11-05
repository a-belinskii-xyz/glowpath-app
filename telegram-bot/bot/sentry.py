from __future__ import annotations

from typing import Any

import sentry_sdk

from bot.config import settings

# Render probes /health every few seconds; tracing those only burns quota.
_UNTRACED_TRANSACTIONS = frozenset({"/health"})


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
    if not settings.sentry_dsn:
        return
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
        enable_logs=True,
    )
