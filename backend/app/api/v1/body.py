import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.body import BodySettings, FoodLog, Measurement
from app.models.user import User
from app.schemas.body import (
    BodySettingsPatch,
    BodySettingsPublic,
    FoodLogCreate,
    FoodLogListResponse,
    FoodLogPatch,
    FoodLogPublic,
    WeightListResponse,
    WeightPublic,
    WeightWrite,
)
from app.services.body_service import (
    BodyError,
    add_food,
    delete_food,
    delete_weight,
    get_settings,
    list_food,
    list_weights,
    patch_food,
    patch_settings,
    set_weight,
)

router = APIRouter(tags=["body"])


def _settings_public(settings: BodySettings) -> BodySettingsPublic:
    return BodySettingsPublic(
        show_weight=settings.show_weight,
        show_food=settings.show_food,
        hide_weight=settings.hide_weight,
        food_goal_id=settings.food_goal_id,
    )


def _weight_public(measurement: Measurement) -> WeightPublic:
    return WeightPublic(day=measurement.day, value=float(measurement.value))


def _food_public(log: FoodLog) -> FoodLogPublic:
    return FoodLogPublic.model_validate(log, from_attributes=True)


@router.get("/settings", response_model=BodySettingsPublic)
def read_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> BodySettingsPublic:
    return _settings_public(get_settings(db, user_id=current_user.id))


@router.patch("/settings", response_model=BodySettingsPublic)
def update_settings(
    body: BodySettingsPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> BodySettingsPublic:
    try:
        settings = patch_settings(
            db,
            user_id=current_user.id,
            show_weight=body.show_weight,
            show_food=body.show_food,
            hide_weight=body.hide_weight,
            food_goal_id=body.food_goal_id,
            food_goal_id_set="food_goal_id" in body.model_fields_set,
        )
    except BodyError as exc:
        raise_http_error(exc)
    return _settings_public(settings)


@router.get("/weight", response_model=WeightListResponse)
def read_weights(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WeightListResponse:
    try:
        items = list_weights(db, user_id=current_user.id, date_from=date_from, date_to=date_to)
    except BodyError as exc:
        raise_http_error(exc)
    return WeightListResponse(items=[_weight_public(item) for item in items])


@router.put("/weight/{day}", response_model=WeightPublic)
def put_weight(
    day: date,
    body: WeightWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WeightPublic:
    try:
        measurement = set_weight(db, user=current_user, day=day, value=body.value)
    except BodyError as exc:
        raise_http_error(exc)
    return _weight_public(measurement)


@router.delete("/weight/{day}", status_code=status.HTTP_204_NO_CONTENT)
def remove_weight(
    day: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    delete_weight(db, user_id=current_user.id, day=day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/food", response_model=FoodLogListResponse)
def read_food(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> FoodLogListResponse:
    try:
        items = list_food(db, user_id=current_user.id, date_from=date_from, date_to=date_to)
    except BodyError as exc:
        raise_http_error(exc)
    return FoodLogListResponse(items=[_food_public(item) for item in items])


@router.post("/food", response_model=FoodLogPublic, status_code=status.HTTP_201_CREATED)
def create_food(
    body: FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> FoodLogPublic:
    try:
        log = add_food(db, user=current_user, day=body.day, meal=body.meal, text=body.text)
    except BodyError as exc:
        raise_http_error(exc)
    return _food_public(log)


@router.patch("/food/{log_id}", response_model=FoodLogPublic)
def update_food(
    log_id: uuid.UUID,
    body: FoodLogPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> FoodLogPublic:
    try:
        log = patch_food(
            db,
            user_id=current_user.id,
            log_id=log_id,
            meal=body.meal,
            meal_set="meal" in body.model_fields_set,
            text=body.text,
        )
    except BodyError as exc:
        raise_http_error(exc)
    return _food_public(log)


@router.delete("/food/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_food(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_food(db, user_id=current_user.id, log_id=log_id)
    except BodyError as exc:
        raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
