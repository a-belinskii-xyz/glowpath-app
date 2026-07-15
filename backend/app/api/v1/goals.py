import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale
from app.config import settings
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalListResponse,
    GoalPatch,
    GoalPublic,
    GoalReorderRequest,
)
from app.services.goal_service import (
    GoalError,
    create_goal,
    delete_goal,
    list_goals,
    load_goals_week_stats,
    patch_goal,
    reorder_goals,
    serialize_goal,
    serialize_goals,
)

router = APIRouter(tags=["goals"])


def _handle_error(exc: GoalError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _to_public(goal: Goal, *, locale: str, completed_this_week: int = 0) -> GoalPublic:
    return GoalPublic.model_validate(
        serialize_goal(goal, locale=locale, completed_this_week=completed_this_week)
    )


def _to_list_response(
    db: Session,
    *,
    user: User,
    goals: list[Goal],
    locale: str,
) -> GoalListResponse:
    counts = load_goals_week_stats(db, user=user, goals=goals)
    items = [
        GoalPublic.model_validate(item)
        for item in serialize_goals(goals, locale=locale, completed_by_goal=counts)
    ]
    return GoalListResponse(
        items=items,
        entry_visible_goal_limit=settings.entry_visible_goal_limit,
    )


@router.get("", response_model=GoalListResponse)
def get_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> GoalListResponse:
    goals = list_goals(db, user_id=current_user.id)
    return _to_list_response(db, user=current_user, goals=goals, locale=locale)


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
            starts_on=body.starts_on,
            slug=body.slug,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    counts = load_goals_week_stats(db, user=current_user, goals=[goal])
    return _to_public(goal, locale=locale, completed_this_week=counts.get(goal.id, 0))


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
            starts_on=body.starts_on,
            sort_order=body.sort_order,
            show_on_entry=body.show_on_entry,
        )
    except GoalError as exc:
        _handle_error(exc)
        raise
    counts = load_goals_week_stats(db, user=current_user, goals=[goal])
    return _to_public(goal, locale=locale, completed_this_week=counts.get(goal.id, 0))


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
