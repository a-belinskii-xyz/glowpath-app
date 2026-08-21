"""Server-side feature flags with kill switch, percent rollout, and allowlists.

A user sees a flag when:

1. The master switch is on, AND
2. Their email or user id is allowlisted, OR they fall in the percent bucket.

Master off is an instant rollback for everyone, including allowlists.
Percent assignment is a stable hash of ``flag:user_id`` (not random per request).

TODO: move targeting rules from env/`Settings` into a DB table so flags can be
toggled without restarting the server. Keep this evaluation API
(``is_feature_enabled`` / ``features_for_user``) as the single entry point.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.config import settings


class FeatureUser(Protocol):
    id: uuid.UUID
    email: str


class FeatureFlag(StrEnum):
    WEEKLY_FREQUENT_TAGS = "weekly_frequent_tags"
    ICON_MARKETPLACE = "icon_marketplace"
    ACHIEVEMENTS = "achievements"


@dataclass(frozen=True)
class FeatureTargeting:
    enabled: bool
    percent: int
    emails: frozenset[str]
    user_ids: frozenset[uuid.UUID]


def parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def parse_uuid_csv(raw: str) -> frozenset[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for part in parse_csv(raw):
        try:
            ids.add(uuid.UUID(part))
        except ValueError:
            continue
    return frozenset(ids)


def targeting_for(flag: FeatureFlag) -> FeatureTargeting:
    # TODO: load FeatureTargeting from DB instead of process-lifetime settings.
    if flag is FeatureFlag.WEEKLY_FREQUENT_TAGS:
        return FeatureTargeting(
            enabled=settings.feature_weekly_frequent_tags,
            percent=settings.feature_weekly_frequent_tags_percent,
            emails=frozenset(
                email.lower() for email in parse_csv(settings.feature_weekly_frequent_tags_emails)
            ),
            user_ids=parse_uuid_csv(settings.feature_weekly_frequent_tags_user_ids),
        )
    if flag is FeatureFlag.ICON_MARKETPLACE:
        return FeatureTargeting(
            enabled=settings.feature_icon_marketplace,
            percent=settings.feature_icon_marketplace_percent,
            emails=frozenset(
                email.lower() for email in parse_csv(settings.feature_icon_marketplace_emails)
            ),
            user_ids=parse_uuid_csv(settings.feature_icon_marketplace_user_ids),
        )
    if flag is FeatureFlag.ACHIEVEMENTS:
        return FeatureTargeting(
            enabled=settings.feature_achievements,
            percent=settings.feature_achievements_percent,
            emails=frozenset(
                email.lower() for email in parse_csv(settings.feature_achievements_emails)
            ),
            user_ids=parse_uuid_csv(settings.feature_achievements_user_ids),
        )
    raise ValueError(f"Unknown feature flag: {flag}")


def stable_bucket(flag: FeatureFlag, user_id: uuid.UUID) -> int:
    """Return 0–99, stable across deploys for the same user and flag."""
    digest = hashlib.sha256(f"{flag}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:2], "big") % 100


def is_feature_enabled(
    flag: FeatureFlag,
    *,
    user_id: uuid.UUID,
    email: str,
) -> bool:
    rule = targeting_for(flag)
    if not rule.enabled:
        return False
    if email.lower() in rule.emails or user_id in rule.user_ids:
        return True
    if rule.percent <= 0:
        return False
    if rule.percent >= 100:
        return True
    return stable_bucket(flag, user_id) < rule.percent


def is_feature_enabled_for_user(flag: FeatureFlag, user: FeatureUser) -> bool:
    return is_feature_enabled(flag, user_id=user.id, email=user.email)


def features_for_user(user: FeatureUser) -> dict[str, bool]:
    return {
        FeatureFlag.WEEKLY_FREQUENT_TAGS.value: is_feature_enabled_for_user(
            FeatureFlag.WEEKLY_FREQUENT_TAGS,
            user,
        ),
        FeatureFlag.ICON_MARKETPLACE.value: is_feature_enabled_for_user(
            FeatureFlag.ICON_MARKETPLACE,
            user,
        ),
        FeatureFlag.ACHIEVEMENTS.value: is_feature_enabled_for_user(
            FeatureFlag.ACHIEVEMENTS,
            user,
        ),
    }
