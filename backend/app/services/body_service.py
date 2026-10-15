"""Weight and food on «Моё» (GP-47): gentle records with no targets or calories."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.body import BodySettings, FoodLog, Measurement
from app.models.goal import Goal
from app.models.user import User
from app.services.goal_service import user_today

WEIGHT = "weight"
# Enough for the "year" chart with a little room; keeps one request bounded.
MAX_RANGE_DAYS = 400


class BodyError(AppError):
    pass


def get_settings(db: Session, *, user_id: uuid.UUID) -> BodySettings:
    settings = db.get(BodySettings, user_id)
    if settings is None:
        settings = BodySettings(
            user_id=user_id, show_weight=False, show_food=False, hide_weight=False
        )
    return settings


def patch_settings(
    db: Session,
    *,
    user_id: uuid.UUID,
    show_weight: bool | None,
    show_food: bool | None,
    hide_weight: bool | None,
    food_goal_id: uuid.UUID | None,
    food_goal_id_set: bool,
) -> BodySettings:
    settings = db.get(BodySettings, user_id)
    if settings is None:
        settings = BodySettings(
            user_id=user_id, show_weight=False, show_food=False, hide_weight=False
        )
        db.add(settings)
    if show_weight is not None:
        settings.show_weight = show_weight
    if show_food is not None:
        settings.show_food = show_food
    if hide_weight is not None:
        settings.hide_weight = hide_weight
    if food_goal_id_set:
        if food_goal_id is not None:
            owned = db.scalar(
                select(Goal.id).where(Goal.id == food_goal_id, Goal.user_id == user_id)
            )
            if owned is None:
                raise BodyError("Goal not found", code=ErrorCode.GOAL_NOT_FOUND, status_code=404)
        settings.food_goal_id = food_goal_id
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
