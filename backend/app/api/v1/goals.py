import uuid
from datetime import date, datetime
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.config import settings
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.models.user_goal_icon import UserGoalIcon
from app.schemas.goal import (
    GoalCalendarResponse,
    GoalCheckinRequest,
    GoalCreate,
    GoalIconListResponse,
    GoalIconMetaPublic,
    GoalIconPublic,
    GoalListResponse,
    GoalPatch,
    GoalPublic,
    GoalReorderRequest,
    GoalStatsResponse,
)
from app.services.achievements.service import evaluate_user_achievements
from app.services.goal_icon_service import (
    MAX_ICONS_PER_GOAL,
    GoalIconError,
    delete_goal_icon_by_id,
    download_goal_icon,
    download_goal_icon_source,
    list_goal_icons,
    upload_goal_icon,
)
from app.services.goal_service import (
    GoalError,
    GoalPeriodProgress,
    create_goal,
    delete_goal,
    delete_goal_checkin,
    get_goal_calendar,
    get_goal_stats,
    list_goals,
    load_goals_week_stats,
    patch_goal,
    reorder_goals,
    serialize_goal,
    serialize_goals,
    set_goal_checkin,
    user_today,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["goals"])


def _handle_error(exc: GoalError) -> None:
    raise_http_error(exc)


def _handle_icon_error(exc: GoalIconError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


def _to_public(
    goal: Goal,
    *,
    locale: str,
    completed_this_week: int = 0,
    day_amount: int = 0,
    week_marks: list[dict[str, Any]] | None = None,
) -> GoalPublic:
    return GoalPublic.model_validate(
        serialize_goal(
            goal,
            locale=locale,
            completed_this_week=completed_this_week,
            day_amount=day_amount,
            week_marks=week_marks,
        )
    )


def _to_list_response(
    db: Session,
    *,
    user: User,
    goals: list[Goal],
    locale: str,
    progress_on: date | None = None,
) -> GoalListResponse:
    progress = load_goals_week_stats(db, user=user, goals=goals, reference_date=progress_on)
    items = [
        GoalPublic.model_validate(item)
        for item in serialize_goals(
            goals,
            locale=locale,
            completed_by_goal={goal_id: item.completed_days for goal_id, item in progress.items()},
            day_amount_by_goal={
                goal_id: item.amount_on(progress_on or _user_today(user))
                for goal_id, item in progress.items()
            },
            week_marks_by_goal={goal_id: item.marks() for goal_id, item in progress.items()},
        )
    ]
    return GoalListResponse(
        items=items,
        entry_visible_goal_limit=settings.entry_visible_goal_limit,
        stats_visible_goal_limit=settings.stats_visible_goal_limit,
    )


def _snapshot(
    progress: dict[uuid.UUID, GoalPeriodProgress],
    goal_id: uuid.UUID,
    *,
    day: date,
) -> tuple[int, int]:
    item = progress.get(goal_id)
    if item is None:
        return 0, 0
    return item.completed_days, item.amount_on(day)


def _public_with_week_stats(
    db: Session, user: User, goal: Goal, locale: str, *, progress_on: date | None = None
) -> GoalPublic:
    day = progress_on or _user_today(user)
    progress = load_goals_week_stats(db, user=user, goals=[goal], reference_date=day)
    completed, day_amount = _snapshot(progress, goal.id, day=day)
    item = progress.get(goal.id)
    return _to_public(
        goal,
        locale=locale,
        completed_this_week=completed,
        day_amount=day_amount,
        week_marks=item.marks() if item is not None else None,
    )


def _user_today(user: User) -> date:
    return user_today(user.timezone)


def _icon_meta(icon: UserGoalIcon) -> GoalIconMetaPublic:
    return GoalIconMetaPublic(
        id=icon.id,
        goal_id=icon.goal_id,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
    )


@router.get("", response_model=GoalListResponse)
def get_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
    progress_on: Annotated[date | None, Query()] = None,
) -> GoalListResponse:
    goals = list_goals(db, user_id=current_user.id)
    return _to_list_response(
        db, user=current_user, goals=goals, locale=locale, progress_on=progress_on
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GoalPublic)
def create_goal_endpoint(
    body: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalPublic:
    try:
        goal = create_goal(
            db,
            user_id=current_user.id,
            labels=body.labels,
            times_per_week=body.times_per_week,
            tracking_kind=body.tracking_kind,
            target_amount=body.target_amount,
            unit=body.unit,
            partial_label=body.partial_label,
            min_amount=body.min_amount,
            starts_on=body.starts_on,
            ends_on=body.ends_on,
            slug=body.slug,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
            show_in_stats=body.show_in_stats,
            color=body.color,
            icon_type=body.icon_type.value if body.icon_type is not None else None,
            icon=body.icon,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    evaluate_user_achievements(db, user=current_user, locale=locale)
    db.commit()
    return _public_with_week_stats(db, current_user, goal, locale)


@router.get("/calendar", response_model=GoalCalendarResponse)
def calendar_goals(
    recorded_from: Annotated[datetime, Query()],
    recorded_to: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> GoalCalendarResponse:
    try:
        days = get_goal_calendar(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    return GoalCalendarResponse.model_validate({"days": days})


@router.get("/stats", response_model=GoalStatsResponse)
def stats_goals(
    recorded_from: Annotated[datetime, Query()],
    recorded_to: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalStatsResponse:
    try:
        payload = get_goal_stats(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            locale=locale,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    return GoalStatsResponse.model_validate(payload)


@router.put("/reorder", response_model=GoalListResponse)
def reorder_goals_endpoint(
    body: GoalReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalListResponse:
    try:
        goals = reorder_goals(
            db,
            user_id=current_user.id,
            ordered_ids=body.ordered_ids,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    return _to_list_response(db, user=current_user, goals=goals, locale=locale)


@router.get("/icons/id/{icon_id}")
def download_goal_icon_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_goal_icon(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except GoalIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    filename = quote(icon.original_name)
    return FastAPIResponse(
        content=data,
        media_type=icon.mime_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
        },
    )


@router.get("/icons/id/{icon_id}/source")
def download_goal_icon_source_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_goal_icon_source(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except GoalIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    filename = quote(icon.original_name)
    return FastAPIResponse(
        content=data,
        media_type=icon.source_mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
        },
    )


@router.delete(
    "/icons/id/{icon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_goal_icon_endpoint(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        delete_goal_icon_by_id(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except GoalIconError as exc:
        _handle_icon_error(exc)
        raise
    except GoalError as exc:
        _handle_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/icons", response_model=GoalIconListResponse)
def list_goal_icons_endpoint(
    goal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> GoalIconListResponse:
    try:
        icons = list_goal_icons(db, user_id=current_user.id, goal_id=goal_id)
    except GoalError as exc:
        _handle_error(exc)
        raise
    return GoalIconListResponse(
        items=[_icon_meta(icon) for icon in icons],
        max_per_goal=MAX_ICONS_PER_GOAL,
    )


@router.post(
    "/{goal_id}/icons",
    status_code=status.HTTP_201_CREATED,
    response_model=GoalIconPublic,
)
async def upload_goal_icon_endpoint(
    goal_id: uuid.UUID,
    file: UploadFile = File(),
    source: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> GoalIconPublic:
    data = await file.read()
    original_name = file.filename or "icon"
    content_type = file.content_type or "application/octet-stream"
    source_data: bytes | None = None
    source_content_type: str | None = None
    source_original_name: str | None = None
    if source is not None:
        source_data = await source.read()
        source_content_type = source.content_type or "application/octet-stream"
        source_original_name = source.filename or original_name
    try:
        icon, goal = upload_goal_icon(
            db,
            user_id=current_user.id,
            goal_id=goal_id,
            data=data,
            content_type=content_type,
            original_name=original_name,
            storage=storage,
            source_data=source_data,
            source_content_type=source_content_type,
            source_original_name=source_original_name,
        )
    except GoalIconError as exc:
        _handle_icon_error(exc)
        raise
    except GoalError as exc:
        _handle_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    counts = load_goals_week_stats(db, user=current_user, goals=[goal])
    completed, day_amount = _snapshot(
        progress=counts, goal_id=goal.id, day=_user_today(current_user)
    )
    return GoalIconPublic(
        id=icon.id,
        goal_id=icon.goal_id,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
        goal=_to_public(
            goal,
            locale=locale,
            completed_this_week=completed,
            day_amount=day_amount,
        ),
    )


@router.patch("/{goal_id}", response_model=GoalPublic)
def update_goal(
    goal_id: uuid.UUID,
    body: GoalPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalPublic:
    try:
        goal = patch_goal(
            db,
            user_id=current_user.id,
            goal_id=goal_id,
            slug=body.slug,
            labels=body.labels,
            times_per_week=body.times_per_week,
            tracking_kind=body.tracking_kind,
            target_amount=body.target_amount,
            target_amount_set="target_amount" in body.model_fields_set,
            unit=body.unit,
            unit_set="unit" in body.model_fields_set,
            partial_label=body.partial_label,
            partial_label_set="partial_label" in body.model_fields_set,
            min_amount=body.min_amount,
            min_amount_set="min_amount" in body.model_fields_set,
            starts_on=body.starts_on,
            ends_on=body.ends_on,
            ends_on_set="ends_on" in body.model_fields_set,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
            show_in_stats=body.show_in_stats,
            color=body.color,
            icon_type=body.icon_type.value if body.icon_type is not None else None,
            icon=body.icon,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    return _public_with_week_stats(db, current_user, goal, locale)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_goal(
    goal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> Response:
    try:
        delete_goal(db, user_id=current_user.id, goal_id=goal_id)
    except GoalError as exc:
        _handle_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{goal_id}/checkins/{day}", response_model=GoalPublic)
def put_goal_checkin(
    goal_id: uuid.UUID,
    day: date,
    body: GoalCheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalPublic:
    """Mark a goal done on ``day`` without a mood entry; the response covers that day's week."""
    try:
        goal = set_goal_checkin(
            db,
            user=current_user,
            goal_id=goal_id,
            day=day,
            level=body.level,
            amount=body.amount,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    return _public_with_week_stats(db, current_user, goal, locale, progress_on=day)


@router.delete("/{goal_id}/checkins/{day}", response_model=GoalPublic)
def remove_goal_checkin(
    goal_id: uuid.UUID,
    day: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalPublic:
    try:
        goal = delete_goal_checkin(db, user=current_user, goal_id=goal_id, day=day)
    except GoalError as exc:
        _handle_error(exc)
        raise
    return _public_with_week_stats(db, current_user, goal, locale, progress_on=day)
