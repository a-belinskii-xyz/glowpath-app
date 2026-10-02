"""Achievements API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_user
from app.db.session import get_db
from app.models.achievement import Achievement
from app.models.achievement_reward import AchievementReward
from app.models.catalog_icon import CatalogIcon
from app.models.user import User
from app.schemas.achievement import (
    AchievementListResponse,
    AchievementPublic,
    AchievementSummaryResponse,
)
from app.services.achievements import (
    AchievementError,
    achievements_summary,
    list_achievements_for_user,
    mark_achievement_seen,
)
from app.services.achievements.service import rewards_visible, serialize_achievement_public
from app.services.achievements.staff import download_achievement_icon
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["achievements"])


def _require_achievements(user: User) -> None:
    if not is_feature_enabled_for_user(FeatureFlag.ACHIEVEMENTS, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.ACHIEVEMENTS_DISABLED,
                message="Achievements are not enabled for this user",
            ),
        )


@router.get("", response_model=AchievementListResponse)
def get_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> AchievementListResponse:
    _require_achievements(current_user)
    items = list_achievements_for_user(db, user=current_user, locale=locale)
    db.commit()
    return AchievementListResponse(items=[AchievementPublic.model_validate(item) for item in items])


@router.get("/summary", response_model=AchievementSummaryResponse)
def get_achievements_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> AchievementSummaryResponse:
    _require_achievements(current_user)
    summary = achievements_summary(db, user=current_user, locale=locale)
    db.commit()
    return AchievementSummaryResponse.model_validate(summary)


@router.get("/{achievement_id}/icon")
def get_achievement_icon(
    achievement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        achievement, data = download_achievement_icon(
            db,
            user=current_user,
            achievement_id=achievement_id,
            storage=storage,
        )
    except (AchievementError, StorageError) as exc:
        raise_http_error(exc)
    return Response(
        content=data,
        media_type=achievement.icon_mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/{achievement_id}/seen", response_model=AchievementPublic)
def post_achievement_seen(
    achievement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> AchievementPublic:
    _require_achievements(current_user)
    try:
        progress = mark_achievement_seen(
            db,
            user=current_user,
            achievement_id=achievement_id,
        )
        achievement = db.scalar(
            select(Achievement)
            .where(Achievement.id == achievement_id)
            .options(
                selectinload(Achievement.rewards).selectinload(AchievementReward.pack),
                selectinload(Achievement.rewards)
                .selectinload(AchievementReward.catalog_icon)
                .selectinload(CatalogIcon.pack),
            )
        )
        if achievement is None:
            raise AchievementError(
                "Achievement not found",
                code=ErrorCode.ACHIEVEMENT_NOT_FOUND,
                status_code=404,
            )
        payload = serialize_achievement_public(
            db,
            achievement,
            progress=progress,
            locale=locale,
            show_rewards=rewards_visible(current_user),
        )
        db.commit()
    except AchievementError as exc:
        db.rollback()
        raise_http_error(exc)
        raise
    return AchievementPublic.model_validate(payload)
