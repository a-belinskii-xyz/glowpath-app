"""Icon marketplace domain constants."""

from __future__ import annotations

from enum import StrEnum


class PackStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WalletLedgerKind(StrEnum):
    GRANT = "grant"
    UNLOCK_PACK = "unlock_pack"
    ADJUSTMENT = "adjustment"
    REFUND = "refund"
    ACHIEVEMENT = "achievement"


class IconUsage(StrEnum):
    """Where a catalog icon is recommended; users may still put it anywhere."""

    MOOD = "mood"
    TAG = "tag"
    GOAL = "goal"


PACK_STATUSES = frozenset(status.value for status in PackStatus)
WALLET_LEDGER_KINDS = frozenset(kind.value for kind in WalletLedgerKind)
ICON_USAGES = tuple(usage.value for usage in IconUsage)

MAX_CATALOG_ICON_BYTES = 512 * 1024
MAX_SUGGESTED_COLORS = 8
MIN_SUGGESTED_COLORS = 1
MAX_SEARCH_TAGS_PER_ICON = 12
ESSENTIALS_PACK_SLUG = "essentials"
DEMO_MOCKS_PACK_SLUG = "demo-mocks"


ALLOWED_CATALOG_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/svg+xml",
    }
)


ICON_CROP_KEYS = ("x", "y", "w", "h")
ICON_CROP_HEADER = "X-Icon-Crop"
# Rounds away float noise from the browser so x + w can land exactly on 1.
_CROP_EPSILON = 1e-6


def parse_icon_crop(raw: object) -> dict[str, float] | None:
    """Validate a crop frame (fractions of the image size); None when it is not one."""
    if not isinstance(raw, dict) or set(raw) != set(ICON_CROP_KEYS):
        return None
    values: dict[str, float] = {}
    for key in ICON_CROP_KEYS:
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        values[key] = round(float(value), 6)
    x, y, w, h = (values[key] for key in ICON_CROP_KEYS)
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return None
    if x + w > 1 + _CROP_EPSILON or y + h > 1 + _CROP_EPSILON:
        return None
    return values


def parse_icon_usage(raw: object) -> list[str] | None:
    """Deduplicated usage list in canonical order; None when an item is unknown."""
    if not isinstance(raw, list):
        return None
    items = set()
    for item in raw:
        if not isinstance(item, str) or item not in ICON_USAGES:
            return None
        items.add(item)
    return [usage for usage in ICON_USAGES if usage in items]
