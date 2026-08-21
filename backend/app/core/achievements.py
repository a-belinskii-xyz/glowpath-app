"""Achievement domain constants."""

from __future__ import annotations

from enum import StrEnum


class AchievementCategory(StrEnum):
    GETTING_STARTED = "getting_started"
    STREAKS = "streaks"
    COLLECTION = "collection"
    SECRETS = "secrets"


class AchievementVisibility(StrEnum):
    VISIBLE = "visible"
    SECRET = "secret"


class AchievementStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AchievementRewardKind(StrEnum):
    TOKENS = "tokens"
    ICON_PACK = "icon_pack"
    CATALOG_ICON = "catalog_icon"


class CriteriaType(StrEnum):
    ENTRY_COUNT = "entry_count"
    CONSECUTIVE_DAYS = "consecutive_days"
    CALENDAR_MATCH = "calendar_match"


ACHIEVEMENT_CATEGORIES = frozenset(c.value for c in AchievementCategory)
ACHIEVEMENT_VISIBILITIES = frozenset(v.value for v in AchievementVisibility)
ACHIEVEMENT_STATUSES = frozenset(s.value for s in AchievementStatus)
ACHIEVEMENT_REWARD_KINDS = frozenset(k.value for k in AchievementRewardKind)
CRITERIA_TYPES = frozenset(t.value for t in CriteriaType)

DEFAULT_ACHIEVEMENT_ICON_TYPE = "emoji"
DEFAULT_ACHIEVEMENT_ICON = "🏆"
