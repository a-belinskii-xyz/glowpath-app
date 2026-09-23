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
    ENTRIES_WITH_NOTE = "entries_with_note"
    FAVORITE_COUNT = "favorite_count"
    SCORE_COUNT = "score_count"
    DISTINCT_SCORES = "distinct_scores"
    ATTACHMENT_COUNT = "attachment_count"
    TAGGED_ENTRY_COUNT = "tagged_entry_count"
    DISTINCT_TAGS_USED = "distinct_tags_used"
    GOAL_CREATED_COUNT = "goal_created_count"
    GOAL_CHECKIN_COUNT = "goal_checkin_count"
    SOURCE_PREFIX = "source_prefix"
    LOCAL_HOUR_RANGE = "local_hour_range"
    DISTINCT_CHECKIN_DAYS = "distinct_checkin_days"


ACHIEVEMENT_CATEGORIES = frozenset(c.value for c in AchievementCategory)
ACHIEVEMENT_VISIBILITIES = frozenset(v.value for v in AchievementVisibility)
ACHIEVEMENT_STATUSES = frozenset(s.value for s in AchievementStatus)
ACHIEVEMENT_REWARD_KINDS = frozenset(k.value for k in AchievementRewardKind)
CRITERIA_TYPES = frozenset(t.value for t in CriteriaType)

DEFAULT_ACHIEVEMENT_ICON_TYPE = "emoji"
DEFAULT_ACHIEVEMENT_ICON = "🏆"
