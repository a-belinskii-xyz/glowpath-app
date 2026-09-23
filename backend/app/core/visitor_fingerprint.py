"""First-party visitor fingerprint hashing for guest experiment stickiness."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.config import settings


def canonical_fingerprint_payload(
    *,
    user_agent: str,
    accept_language: str,
    timezone: str,
    screen_width: int,
    screen_height: int,
    screen_dpr: float,
    platform: str,
    max_touch_points: int,
) -> dict[str, Any]:
    return {
        "accept_language": accept_language.strip().lower(),
        "max_touch_points": max_touch_points,
        "platform": platform.strip(),
        "screen_dpr": round(float(screen_dpr), 2),
        "screen_height": int(screen_height),
        "screen_width": int(screen_width),
        "timezone": timezone.strip(),
        "user_agent": user_agent.strip(),
    }


def fingerprint_hash_from_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hmac.new(
        settings.guest_experiment_secret.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest
