from enum import StrEnum

MAX_GOAL_AMOUNT = 1_000_000
MAX_GOAL_UNIT_LENGTH = 32
MAX_GOAL_PARTIAL_LABEL_LENGTH = 80


class GoalTrackingKind(StrEnum):
    BINARY = "binary"
    QUANTITY = "quantity"


class GoalCheckinLevel(StrEnum):
    PARTIAL = "partial"
    FULL = "full"


# A quantity day with some progress that does not count yet (GP-46); never stored.
GOAL_DAY_STARTED = "started"
