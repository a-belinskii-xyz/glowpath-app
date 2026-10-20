import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.body import BodySettings, Exercise, FoodLog, Measurement, SleepLog, WorkoutSet
from app.models.user import User
from app.schemas.body import (
    BodySettingsPatch,
    BodySettingsPublic,
    ExerciseCreate,
    ExerciseListResponse,
    ExercisePatch,
    ExercisePublic,
    FoodLogCreate,
    FoodLogListResponse,
    FoodLogPatch,
    FoodLogPublic,
    SleepListResponse,
    SleepPublic,
    SleepWrite,
    WeightListResponse,
    WeightPublic,
    WeightWrite,
    WorkoutListResponse,
    WorkoutSetPublic,
    WorkoutWrite,
)
from app.services.body_service import (
    BodyError,
    add_exercise,
    add_food,
    delete_exercise,
    delete_food,
    delete_sleep,
    delete_weight,
    food_goal_ids,
    get_settings,
    list_exercises,
    list_food,
    list_sleep,
    list_weights,
    list_workout_sets,
    patch_exercise,
    patch_food,
    patch_settings,
    set_sleep,
    set_weight,
    set_workout,
)

router = APIRouter(tags=["body"])


def _settings_public(db: Session, settings: BodySettings) -> BodySettingsPublic:
    return BodySettingsPublic(
        show_weight=settings.show_weight,
        show_food=settings.show_food,
        hide_weight=settings.hide_weight,
        show_sleep=settings.show_sleep,
        height_cm=float(settings.height_cm) if settings.height_cm is not None else None,
        show_workouts=settings.show_workouts,
        sleep_norm_min=settings.sleep_norm_min,
        sleep_norm_max=settings.sleep_norm_max,
        food_goal_ids=food_goal_ids(db, user_id=settings.user_id),
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
    return _settings_public(db, get_settings(db, user_id=current_user.id))


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
            goal_ids=body.food_goal_ids,
            show_sleep=body.show_sleep,
            height_cm=body.height_cm,
            height_set="height_cm" in body.model_fields_set,
            show_workouts=body.show_workouts,
            sleep_norm=(
                (body.sleep_norm_min, body.sleep_norm_max)
                if "sleep_norm_min" in body.model_fields_set
                else None
            ),
        )
    except BodyError as exc:
        raise_http_error(exc)
    return _settings_public(db, settings)


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


def _sleep_public(log: SleepLog) -> SleepPublic:
    return SleepPublic.model_validate(log, from_attributes=True)


@router.get("/sleep", response_model=SleepListResponse)
def read_sleep(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> SleepListResponse:
    try:
        items = list_sleep(db, user_id=current_user.id, date_from=date_from, date_to=date_to)
    except BodyError as exc:
        raise_http_error(exc)
    return SleepListResponse(items=[_sleep_public(item) for item in items])


@router.put("/sleep/{day}", response_model=SleepPublic)
def put_sleep(
    day: date,
    body: SleepWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> SleepPublic:
    """Save the night that ended on the morning of ``day``."""
    try:
        log = set_sleep(
            db,
            user=current_user,
            day=day,
            bed_time=body.bed_time,
            wake_time=body.wake_time,
            up_time=body.up_time,
            quality=body.quality,
            note=body.note,
        )
    except BodyError as exc:
        raise_http_error(exc)
    return _sleep_public(log)


@router.delete("/sleep/{day}", status_code=status.HTTP_204_NO_CONTENT)
def remove_sleep(
    day: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    delete_sleep(db, user_id=current_user.id, day=day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _exercise_public(
    exercise: Exercise, last_day: date | None = None, recent_days: int = 0
) -> ExercisePublic:
    return ExercisePublic(
        id=exercise.id,
        name=exercise.name,
        with_weight=exercise.with_weight,
        last_day=last_day,
        recent_days=recent_days,
    )


def _set_public(row: WorkoutSet) -> WorkoutSetPublic:
    return WorkoutSetPublic(
        exercise_id=row.exercise_id,
        day=row.day,
        position=row.position,
        weight_kg=float(row.weight_kg) if row.weight_kg is not None else None,
        reps=row.reps,
    )


@router.get("/exercises", response_model=ExerciseListResponse)
def read_exercises(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> ExerciseListResponse:
    rows = list_exercises(db, user=current_user)
    return ExerciseListResponse(items=[_exercise_public(*row) for row in rows])


@router.post("/exercises", response_model=ExercisePublic, status_code=status.HTTP_201_CREATED)
def create_exercise(
    body: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> ExercisePublic:
    exercise = add_exercise(
        db, user_id=current_user.id, name=body.name, with_weight=body.with_weight
    )
    return _exercise_public(exercise)


@router.patch("/exercises/{exercise_id}", response_model=ExercisePublic)
def update_exercise(
    exercise_id: uuid.UUID,
    body: ExercisePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> ExercisePublic:
    try:
        exercise = patch_exercise(
            db,
            user_id=current_user.id,
            exercise_id=exercise_id,
            name=body.name,
            with_weight=body.with_weight,
        )
    except BodyError as exc:
        raise_http_error(exc)
    return _exercise_public(exercise)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_exercise(
    exercise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_exercise(db, user_id=current_user.id, exercise_id=exercise_id)
    except BodyError as exc:
        raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/workouts", response_model=WorkoutListResponse)
def read_workouts(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    exercise_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WorkoutListResponse:
    try:
        rows = list_workout_sets(
            db,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            exercise_id=exercise_id,
        )
    except BodyError as exc:
        raise_http_error(exc)
    return WorkoutListResponse(items=[_set_public(row) for row in rows])


@router.put("/workouts/{day}/{exercise_id}", response_model=WorkoutListResponse)
def put_workout(
    day: date,
    exercise_id: uuid.UUID,
    body: WorkoutWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> WorkoutListResponse:
    """Replace the sets of one exercise on ``day``; no sets removes that exercise from the day."""
    try:
        rows = set_workout(
            db,
            user=current_user,
            day=day,
            exercise_id=exercise_id,
            sets=[(item.weight_kg, item.reps) for item in body.sets],
        )
    except BodyError as exc:
        raise_http_error(exc)
    return WorkoutListResponse(items=[_set_public(row) for row in rows])
