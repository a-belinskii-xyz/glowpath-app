"""Weight, food, sleep and workouts on «Моё» (GP-47, GP-48, GP-58): gentle records, no targets."""

import uuid
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.body import (
    BodyFoodGoal,
    BodySettings,
    Exercise,
    FoodLog,
    Measurement,
    SleepLog,
    WorkoutSet,
)
from app.models.goal import Goal
from app.models.user import User
from app.services.goal_service import user_today

WEIGHT = "weight"
# Enough for the "year" chart with a little room; keeps one request bounded.
MAX_RANGE_DAYS = 400
# The window for "how often" an exercise is done, which orders the exercise chips.
RECENT_DAYS = 90


class BodyError(AppError):
    pass


def get_settings(db: Session, *, user_id: uuid.UUID) -> BodySettings:
    settings = db.get(BodySettings, user_id)
    if settings is None:
        settings = BodySettings(
            user_id=user_id,
            show_weight=False,
            show_food=False,
            hide_weight=False,
            show_sleep=False,
            show_workouts=False,
            sleep_norm_min=420,
            sleep_norm_max=540,
        )
    return settings


def food_goal_ids(db: Session, *, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(BodyFoodGoal.goal_id)
            .where(BodyFoodGoal.user_id == user_id)
            .order_by(BodyFoodGoal.position)
        )
    )


def patch_settings(
    db: Session,
    *,
    user_id: uuid.UUID,
    show_weight: bool | None,
    show_food: bool | None,
    hide_weight: bool | None,
    goal_ids: list[uuid.UUID] | None,
    show_sleep: bool | None = None,
    height_cm: Decimal | None = None,
    height_set: bool = False,
    show_workouts: bool | None = None,
    sleep_norm: tuple[int | None, int | None] | None = None,
) -> BodySettings:
    settings = db.get(BodySettings, user_id)
    if settings is None:
        settings = BodySettings(
            user_id=user_id,
            show_weight=False,
            show_food=False,
            hide_weight=False,
            show_sleep=False,
            show_workouts=False,
            sleep_norm_min=420,
            sleep_norm_max=540,
        )
        db.add(settings)
    if show_weight is not None:
        settings.show_weight = show_weight
    if show_food is not None:
        settings.show_food = show_food
    if hide_weight is not None:
        settings.hide_weight = hide_weight
    if show_sleep is not None:
        settings.show_sleep = show_sleep
    if show_workouts is not None:
        settings.show_workouts = show_workouts
    if sleep_norm is not None:
        settings.sleep_norm_min, settings.sleep_norm_max = sleep_norm
    if height_set:
        settings.height_cm = height_cm
    if goal_ids is not None:
        wanted = list(dict.fromkeys(goal_ids))
        owned = set(db.scalars(select(Goal.id).where(Goal.id.in_(wanted), Goal.user_id == user_id)))
        if len(owned) != len(wanted):
            raise BodyError("Goal not found", code=ErrorCode.GOAL_NOT_FOUND, status_code=404)
        db.execute(delete(BodyFoodGoal).where(BodyFoodGoal.user_id == user_id))
        db.add_all(
            BodyFoodGoal(user_id=user_id, goal_id=goal_id, position=index)
            for index, goal_id in enumerate(wanted)
        )
    db.commit()
    db.refresh(settings)
    return settings


def _ensure_range(date_from: date, date_to: date) -> None:
    if date_to < date_from or (date_to - date_from).days > MAX_RANGE_DAYS:
        raise BodyError(
            f"The range must be ordered and at most {MAX_RANGE_DAYS} days",
            code=ErrorCode.INVALID_BODY_RANGE,
        )


def _ensure_not_future(user: User, day: date) -> None:
    # One day of slack: the device may already be past midnight in another timezone.
    if day > user_today(user.timezone) + timedelta(days=1):
        raise BodyError("Cannot record a future day", code=ErrorCode.BODY_DAY_IN_FUTURE)


def list_weights(
    db: Session, *, user_id: uuid.UUID, date_from: date, date_to: date
) -> list[Measurement]:
    _ensure_range(date_from, date_to)
    return list(
        db.scalars(
            select(Measurement)
            .where(
                Measurement.user_id == user_id,
                Measurement.kind == WEIGHT,
                Measurement.day >= date_from,
                Measurement.day <= date_to,
            )
            .order_by(Measurement.day)
        )
    )


def set_weight(db: Session, *, user: User, day: date, value: Decimal) -> Measurement:
    _ensure_not_future(user, day)
    measurement = db.scalar(
        select(Measurement).where(
            Measurement.user_id == user.id, Measurement.kind == WEIGHT, Measurement.day == day
        )
    )
    if measurement is None:
        measurement = Measurement(user_id=user.id, kind=WEIGHT, day=day, value=value)
        db.add(measurement)
    else:
        measurement.value = value
    db.commit()
    db.refresh(measurement)
    return measurement


def delete_weight(db: Session, *, user_id: uuid.UUID, day: date) -> None:
    db.execute(
        delete(Measurement).where(
            Measurement.user_id == user_id, Measurement.kind == WEIGHT, Measurement.day == day
        )
    )
    db.commit()


def list_food(db: Session, *, user_id: uuid.UUID, date_from: date, date_to: date) -> list[FoodLog]:
    _ensure_range(date_from, date_to)
    return list(
        db.scalars(
            select(FoodLog)
            .where(FoodLog.user_id == user_id, FoodLog.day >= date_from, FoodLog.day <= date_to)
            .order_by(FoodLog.day, FoodLog.created_at)
        )
    )


def add_food(db: Session, *, user: User, day: date, meal: str | None, text: str) -> FoodLog:
    _ensure_not_future(user, day)
    log = FoodLog(user_id=user.id, day=day, meal=meal, text=text)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _get_food(db: Session, *, user_id: uuid.UUID, log_id: uuid.UUID) -> FoodLog:
    log = db.scalar(select(FoodLog).where(FoodLog.id == log_id, FoodLog.user_id == user_id))
    if log is None:
        raise BodyError("Food note not found", code=ErrorCode.FOOD_LOG_NOT_FOUND, status_code=404)
    return log


def patch_food(
    db: Session,
    *,
    user_id: uuid.UUID,
    log_id: uuid.UUID,
    meal: str | None,
    meal_set: bool,
    text: str | None,
) -> FoodLog:
    log = _get_food(db, user_id=user_id, log_id=log_id)
    if meal_set:
        log.meal = meal
    if text is not None:
        log.text = text
    db.commit()
    db.refresh(log)
    return log


def delete_food(db: Session, *, user_id: uuid.UUID, log_id: uuid.UUID) -> None:
    db.delete(_get_food(db, user_id=user_id, log_id=log_id))
    db.commit()


def list_sleep(
    db: Session, *, user_id: uuid.UUID, date_from: date, date_to: date
) -> list[SleepLog]:
    _ensure_range(date_from, date_to)
    return list(
        db.scalars(
            select(SleepLog)
            .where(SleepLog.user_id == user_id, SleepLog.day >= date_from, SleepLog.day <= date_to)
            .order_by(SleepLog.day)
        )
    )


def set_sleep(
    db: Session,
    *,
    user: User,
    day: date,
    bed_time: time,
    wake_time: time,
    up_time: time | None,
    quality: str | None,
    note: str | None,
) -> SleepLog:
    _ensure_not_future(user, day)
    log = db.scalar(select(SleepLog).where(SleepLog.user_id == user.id, SleepLog.day == day))
    if log is None:
        log = SleepLog(user_id=user.id, day=day, bed_time=bed_time, wake_time=wake_time)
        db.add(log)
    log.bed_time = bed_time
    log.wake_time = wake_time
    log.up_time = up_time
    log.quality = quality
    log.note = note
    db.commit()
    db.refresh(log)
    return log


def delete_sleep(db: Session, *, user_id: uuid.UUID, day: date) -> None:
    db.execute(delete(SleepLog).where(SleepLog.user_id == user_id, SleepLog.day == day))
    db.commit()


def list_exercises(db: Session, *, user: User) -> list[tuple[Exercise, date | None, int]]:
    """Exercises with their last day and recent days, most recently done first."""
    since = user_today(user.timezone) - timedelta(days=RECENT_DAYS - 1)
    usage = (
        select(
            WorkoutSet.exercise_id,
            func.max(WorkoutSet.day).label("last_day"),
            func.count(func.distinct(WorkoutSet.day))
            .filter(WorkoutSet.day >= since)
            .label("recent_days"),
        )
        .where(WorkoutSet.user_id == user.id)
        .group_by(WorkoutSet.exercise_id)
        .subquery()
    )
    rows = db.execute(
        select(Exercise, usage.c.last_day, usage.c.recent_days)
        .outerjoin(usage, usage.c.exercise_id == Exercise.id)
        .where(Exercise.user_id == user.id)
        .order_by(usage.c.last_day.desc().nulls_last(), Exercise.name)
    ).all()
    return [(exercise, last_day, recent_days or 0) for exercise, last_day, recent_days in rows]


def _find_exercise_by_name(db: Session, *, user_id: uuid.UUID, name: str) -> Exercise | None:
    return db.scalar(
        select(Exercise).where(
            Exercise.user_id == user_id, func.lower(Exercise.name) == name.lower()
        )
    )


def _get_exercise(db: Session, *, user_id: uuid.UUID, exercise_id: uuid.UUID) -> Exercise:
    exercise = db.scalar(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.user_id == user_id)
    )
    if exercise is None:
        raise BodyError("Exercise not found", code=ErrorCode.EXERCISE_NOT_FOUND, status_code=404)
    return exercise


def add_exercise(db: Session, *, user_id: uuid.UUID, name: str, with_weight: bool) -> Exercise:
    """Create an exercise, or return the one already named so (in any letter case)."""
    existing = _find_exercise_by_name(db, user_id=user_id, name=name)
    if existing is not None:
        return existing
    exercise = Exercise(user_id=user_id, name=name, with_weight=with_weight)
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def patch_exercise(
    db: Session,
    *,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    name: str | None,
    with_weight: bool | None,
) -> Exercise:
    exercise = _get_exercise(db, user_id=user_id, exercise_id=exercise_id)
    if name is not None and name != exercise.name:
        other = _find_exercise_by_name(db, user_id=user_id, name=name)
        if other is not None and other.id != exercise.id:
            raise BodyError(
                "An exercise with this name already exists",
                code=ErrorCode.EXERCISE_NAME_TAKEN,
                status_code=409,
            )
        exercise.name = name
    if with_weight is not None:
        exercise.with_weight = with_weight
    db.commit()
    db.refresh(exercise)
    return exercise


def delete_exercise(db: Session, *, user_id: uuid.UUID, exercise_id: uuid.UUID) -> None:
    """Remove an exercise together with all its sets."""
    db.delete(_get_exercise(db, user_id=user_id, exercise_id=exercise_id))
    db.commit()


def list_workout_sets(
    db: Session,
    *,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
    exercise_id: uuid.UUID | None = None,
) -> list[WorkoutSet]:
    _ensure_range(date_from, date_to)
    query = select(WorkoutSet).where(
        WorkoutSet.user_id == user_id, WorkoutSet.day >= date_from, WorkoutSet.day <= date_to
    )
    if exercise_id is not None:
        query = query.where(WorkoutSet.exercise_id == exercise_id)
    return list(db.scalars(query.order_by(WorkoutSet.day, WorkoutSet.position)))


def set_workout(
    db: Session,
    *,
    user: User,
    day: date,
    exercise_id: uuid.UUID,
    sets: list[tuple[Decimal | None, int]],
) -> list[WorkoutSet]:
    """Replace the sets of one exercise on one day; an empty list removes them."""
    _ensure_not_future(user, day)
    exercise = _get_exercise(db, user_id=user.id, exercise_id=exercise_id)
    db.execute(
        delete(WorkoutSet).where(
            WorkoutSet.user_id == user.id,
            WorkoutSet.exercise_id == exercise.id,
            WorkoutSet.day == day,
        )
    )
    rows = [
        WorkoutSet(
            user_id=user.id,
            exercise_id=exercise.id,
            day=day,
            position=index,
            weight_kg=weight if exercise.with_weight else None,
            reps=reps,
        )
        for index, (weight, reps) in enumerate(sets)
    ]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
