import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

MIN_WEIGHT_KG = Decimal("20")
MAX_WEIGHT_KG = Decimal("400")
MAX_FOOD_TEXT_LENGTH = 500
MAX_FOOD_GOALS = 3
MIN_HEIGHT_CM = Decimal("100")
MAX_HEIGHT_CM = Decimal("250")
MAX_SLEEP_NOTE_LENGTH = 500

Meal = Literal["morning", "day", "evening", "snack"]
WeightKg = Annotated[Decimal, Field(ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG, decimal_places=1)]
FoodText = Annotated[str, Field(min_length=1, max_length=MAX_FOOD_TEXT_LENGTH)]
HeightCm = Annotated[Decimal, Field(ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM, decimal_places=1)]
SleepQuality = Literal["hard", "ok", "good"]


class BodySettingsPublic(BaseModel):
    show_weight: bool
    show_food: bool
    hide_weight: bool
    show_sleep: bool = False
    height_cm: float | None = None
    # Goals the food drawer offers to mark, in the order of the settings slots.
    food_goal_ids: list[uuid.UUID] = Field(default_factory=list)


class BodySettingsPatch(BaseModel):
    show_weight: bool | None = None
    show_food: bool | None = None
    hide_weight: bool | None = None
    show_sleep: bool | None = None
    # Send null to forget the height.
    height_cm: HeightCm | None = None
    food_goal_ids: list[uuid.UUID] | None = Field(default=None, max_length=MAX_FOOD_GOALS)


class WeightPublic(BaseModel):
    day: date
    # Kilograms, one decimal; a float keeps the JSON a plain number.
    value: float


class WeightListResponse(BaseModel):
    items: list[WeightPublic]


class WeightWrite(BaseModel):
    value: WeightKg


class FoodLogPublic(BaseModel):
    id: uuid.UUID
    day: date
    meal: Meal | None = None
    text: str
    created_at: datetime


class FoodLogListResponse(BaseModel):
    items: list[FoodLogPublic]


class FoodLogCreate(BaseModel):
    day: date
    meal: Meal | None = None
    text: FoodText

    @field_validator("text", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class FoodLogPatch(BaseModel):
    meal: Meal | None = None
    text: FoodText | None = None

    @field_validator("text", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SleepPublic(BaseModel):
    day: date
    bed_time: time
    wake_time: time
    up_time: time | None = None
    quality: SleepQuality | None = None
    note: str | None = None


class SleepListResponse(BaseModel):
    items: list[SleepPublic]


class SleepWrite(BaseModel):
    bed_time: time
    wake_time: time
    up_time: time | None = None
    quality: SleepQuality | None = None
    note: str | None = Field(default=None, max_length=MAX_SLEEP_NOTE_LENGTH)

    @field_validator("bed_time", "wake_time", "up_time")
    @classmethod
    def _minutes_only(cls, value: time | None) -> time | None:
        return value.replace(second=0, microsecond=0) if value is not None else None

    @field_validator("note", mode="before")
    @classmethod
    def _strip_note(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value
