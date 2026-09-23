from enum import StrEnum

MAX_GOAL_AMOUNT = 1_000_000
MAX_GOAL_UNIT_LENGTH = 32


class GoalTrackingKind(StrEnum):
    BINARY = "binary"
    QUANTITY = "quantity"
