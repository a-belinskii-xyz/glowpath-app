import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MIN_WEIGHT_KG = Decimal("20")
MAX_WEIGHT_KG = Decimal("400")
MAX_FOOD_TEXT_LENGTH = 500
MAX_FOOD_GOALS = 3
MIN_HEIGHT_CM = Decimal("100")
MAX_HEIGHT_CM = Decimal("250")
MAX_SLEEP_NOTE_LENGTH = 500
MAX_EXERCISE_NAME_LENGTH = 80
MAX_SETS_PER_EXERCISE = 30
MAX_SET_WEIGHT_KG = Decimal("999")
MAX_SET_REPS = 1000
# The sleep norm can be set from 3 to 15 hours, in minutes (GP-61).
MIN_SLEEP_NORM = 180
MAX_SLEEP_NORM = 900

Meal = Literal["morning", "day", "evening", "snack"]
WeightKg = Annotated[Decimal, Field(ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG, decimal_places=1)]
FoodText = Annotated[str, Field(min_length=1, max_length=MAX_FOOD_TEXT_LENGTH)]
HeightCm = Annotated[Decimal, Field(ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM, decimal_places=1)]
SleepQuality = Literal["hard", "ok", "good"]
ExerciseName = Annotated[str, Field(min_length=1, max_length=MAX_EXERCISE_NAME_LENGTH)]
SetWeightKg = Annotated[Decimal, Field(ge=0, le=MAX_SET_WEIGHT_KG, decimal_places=2)]
SetReps = Annotated[int, Field(ge=1, le=MAX_SET_REPS)]


def _clean_name(value: object) -> object:
    # "  жим   лёжа " and "жим лёжа" are the same exercise.
    return " ".join(value.split()) if isinstance(value, str) else value


class BodySettingsPublic(BaseModel):
    show_weight: bool
    show_food: bool
    hide_weight: bool
    show_sleep: bool = False
    height_cm: float | None = None
    show_workouts: bool = False
    # Minutes; both null when the person turned the norm off.
    sleep_norm_min: int | None = 420
    sleep_norm_max: int | None = 540
    # Goals the food drawer offers to mark, in the order of the settings slots.
    food_goal_ids: list[uuid.UUID] = Field(default_factory=list)


class BodySettingsPatch(BaseModel):
    show_weight: bool | None = None
    show_food: bool | None = None
    hide_weight: bool | None = None
    show_sleep: bool | None = None
    show_workouts: bool | None = None
    # Send both as null to turn the sleep norm off.
    sleep_norm_min: int | None = Field(default=None, ge=MIN_SLEEP_NORM, le=MAX_SLEEP_NORM)
    sleep_norm_max: int | None = Field(default=None, ge=MIN_SLEEP_NORM, le=MAX_SLEEP_NORM)
    # Send null to forget the height.
    height_cm: HeightCm | None = None
    food_goal_ids: list[uuid.UUID] | None = Field(default=None, max_length=MAX_FOOD_GOALS)

    @model_validator(mode="after")
    def _sleep_norm_together(self) -> "BodySettingsPatch":
        sent = {"sleep_norm_min", "sleep_norm_max"} & self.model_fields_set
        if not sent:
            return self
        if len(sent) == 1:
            raise ValueError("sleep_norm_min and sleep_norm_max are sent together")
        low, high = self.sleep_norm_min, self.sleep_norm_max
        if (low is None) != (high is None):
            raise ValueError("Both sleep norm bounds must be set, or both null")
        if low is not None and high is not None and low >= high:
            raise ValueError("sleep_norm_min must be less than sleep_norm_max")
        return self


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


class ExercisePublic(BaseModel):
    id: uuid.UUID
    name: str
    with_weight: bool
    # The last day with sets, and on how many days of the last 90 it was done.
    last_day: date | None = None
    recent_days: int = 0


class ExerciseListResponse(BaseModel):
    items: list[ExercisePublic]


class ExerciseCreate(BaseModel):
    name: ExerciseName
    with_weight: bool = True

    _clean = field_validator("name", mode="before")(_clean_name)


class ExercisePatch(BaseModel):
    name: ExerciseName | None = None
    with_weight: bool | None = None

    _clean = field_validator("name", mode="before")(_clean_name)


class WorkoutSetWrite(BaseModel):
    weight_kg: SetWeightKg | None = None
    reps: SetReps


class WorkoutWrite(BaseModel):
    sets: list[WorkoutSetWrite] = Field(max_length=MAX_SETS_PER_EXERCISE)


class WorkoutSetPublic(BaseModel):
    exercise_id: uuid.UUID
    day: date
    position: int
    weight_kg: float | None = None
    reps: int


class WorkoutListResponse(BaseModel):
    items: list[WorkoutSetPublic]
