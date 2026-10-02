"""Staff console API: create, edit and archive achievements."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_staff_user, get_locale, get_storage_service
from app.core.achievement_criteria import serialize_criteria_specs
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.achievement import (
    AchievementRewardInput,
    CriteriaSpecListResponse,
    StaffAchievementCreate,
    StaffAchievementListResponse,
    StaffAchievementPatch,
    StaffAchievementPublic,
)
from app.services.achievements import AchievementError
from app.services.achievements.staff import (
    RewardInput,
    create_achievement,
    get_achievement_or_raise,
    list_staff_achievements,
    serialize_staff_achievement,
    set_achievement_icon_image,
    unlocked_counts,
    update_achievement,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["staff"])


def _rewards(items: list[AchievementRewardInput]) -> list[RewardInput]:
    return [
        RewardInput(
            kind=item.kind,
            amount=item.amount,
            pack_id=item.pack_id,
            catalog_icon_id=item.catalog_icon_id,
        )
        for item in items
    ]


def _public(db: Session, achievement_id: uuid.UUID, *, locale: str) -> StaffAchievementPublic:
    achievement = get_achievement_or_raise(db, achievement_id)
    return StaffAchievementPublic.model_validate(
        serialize_staff_achievement(
            achievement,
            locale=locale,
            unlocked_count=unlocked_counts(db).get(achievement.id, 0),
        )
    )


@router.get("/criteria-types", response_model=CriteriaSpecListResponse)
def get_criteria_types(
    _staff: User = Depends(get_current_staff_user),
) -> CriteriaSpecListResponse:
    return CriteriaSpecListResponse.model_validate({"items": serialize_criteria_specs()})


@router.get("", response_model=StaffAchievementListResponse)
def get_staff_achievements(
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> StaffAchievementListResponse:
    counts = unlocked_counts(db)
    return StaffAchievementListResponse(
        items=[
            StaffAchievementPublic.model_validate(
                serialize_staff_achievement(
                    achievement,
                    locale=locale,
                    unlocked_count=counts.get(achievement.id, 0),
                )
            )
            for achievement in list_staff_achievements(db)
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=StaffAchievementPublic)
def post_staff_achievement(
    body: StaffAchievementCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> StaffAchievementPublic:
    try:
        achievement = create_achievement(
            db,
            labels=body.labels.as_labels(),
            descriptions=body.descriptions.as_labels(),
            category=body.category,
            visibility=body.visibility,
            criteria=body.criteria,
            rewards=_rewards(body.rewards),
            emoji=body.emoji,
            slug=body.slug,
            sort_order=body.sort_order,
        )
        db.commit()
    except AchievementError as exc:
        db.rollback()
        raise_http_error(exc)
    return _public(db, achievement.id, locale=locale)


@router.patch("/{achievement_id}", response_model=StaffAchievementPublic)
def patch_staff_achievement(
    achievement_id: uuid.UUID,
    body: StaffAchievementPatch,
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    locale: str = Depends(get_locale),
) -> StaffAchievementPublic:
    try:
        update_achievement(
            db,
            achievement_id=achievement_id,
            labels=body.labels.as_labels() if body.labels is not None else None,
            descriptions=body.descriptions.as_labels() if body.descriptions is not None else None,
            category=body.category,
            visibility=body.visibility,
            status=body.status,
            criteria=body.criteria,
            rewards=_rewards(body.rewards) if body.rewards is not None else None,
            emoji=body.emoji,
            sort_order=body.sort_order,
        )
        db.commit()
    except AchievementError as exc:
        db.rollback()
        raise_http_error(exc)
    return _public(db, achievement_id, locale=locale)


@router.put("/{achievement_id}/icon", response_model=StaffAchievementPublic)
async def put_staff_achievement_icon(
    achievement_id: uuid.UUID,
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    _staff: User = Depends(get_current_staff_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> StaffAchievementPublic:
    data = await file.read()
    try:
        set_achievement_icon_image(
            db,
            achievement_id=achievement_id,
            storage=storage,
            data=data,
            content_type=file.content_type or "",
        )
        db.commit()
    except (AchievementError, StorageError) as exc:
        db.rollback()
        raise_http_error(exc)
    return _public(db, achievement_id, locale=locale)
