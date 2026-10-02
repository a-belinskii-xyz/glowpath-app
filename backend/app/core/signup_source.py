"""Signup source labels from marketing links (GP-21).

Links carry a short label: ``t.me/<bot>?start=src_tiktok``,
``t.me/<bot>/app?startapp=src_tiktok`` or ``<site>/?utm_source=tiktok``.
"""

from __future__ import annotations

import re

SIGNUP_SOURCE_PREFIX = "src_"
DIRECT_SIGNUP_SOURCE = "direct"
_LABEL = re.compile(r"^[a-z0-9_-]{1,32}$")


def normalize_signup_source(raw: str | None) -> str | None:
    """Return a safe lowercase label, or None when the value is missing or malformed."""
    if not raw:
        return None
    value = raw.strip().lower().removeprefix(SIGNUP_SOURCE_PREFIX)
    return value if _LABEL.match(value) else None


def signup_source_from_start_param(start_param: str | None) -> str | None:
    """Mini App / bot start parameters only count as a source with the ``src_`` prefix."""
    if not start_param or not start_param.startswith(SIGNUP_SOURCE_PREFIX):
        return None
    return normalize_signup_source(start_param)
