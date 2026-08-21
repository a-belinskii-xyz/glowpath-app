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


PACK_STATUSES = frozenset(status.value for status in PackStatus)
WALLET_LEDGER_KINDS = frozenset(kind.value for kind in WalletLedgerKind)

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
