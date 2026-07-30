import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.core.errors import raise_http_error
from app.core.i18n import resolve_label
from app.core.mood_builtin_icons import MOOD_BUILTIN_ICONS
from app.db.session import get_db
from app.models.user import User
from app.models.user_mood_icon import UserMoodIcon
from app.schemas.mood_preferences import (
    BuiltinMoodIconPublic,
    MoodIconCatalogResponse,
    MoodIconListResponse,
    MoodIconMetaPublic,
    MoodIconPublic,
    MoodPreferencesPublic,
    MoodPreferencesUpdate,
)
from app.services.mood_icon_service import (
    MAX_ICONS_PER_SCORE,
    MoodIconError,
    delete_mood_icon_by_id,
    download_mood_icon,
    download_mood_icon_source,
    list_mood_icons,
    upload_mood_icon,
)
from app.services.mood_preferences_service import (
    MoodPreferencesError,
    get_or_create_preferences,
    serialize_preferences,
    update_preferences,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["mood-preferences"])


def _handle_preferences_error(exc: MoodPreferencesError) -> None:
    raise_http_error(exc)


def _handle_icon_error(exc: MoodIconError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


def _icon_meta(icon: UserMoodIcon) -> MoodIconMetaPublic:
    return MoodIconMetaPublic(
        id=icon.id,
        score=icon.score,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
    )


@router.get("", response_model=MoodPreferencesPublic)
def get_mood_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodPreferencesPublic:
    prefs = get_or_create_preferences(db, user_id=current_user.id)
    return MoodPreferencesPublic.model_validate(serialize_preferences(db, prefs, locale=locale))


@router.patch("", response_model=MoodPreferencesPublic)
def patch_mood_preferences(
    body: MoodPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodPreferencesPublic:
    updates = {score: patch.model_dump(exclude_unset=True) for score, patch in body.scores.items()}
    try:
        prefs = update_preferences(db, user_id=current_user.id, score_updates=updates)
    except MoodPreferencesError as exc:
        _handle_preferences_error(exc)
        raise
    return MoodPreferencesPublic.model_validate(serialize_preferences(db, prefs, locale=locale))


@router.get("/icon-catalog", response_model=MoodIconCatalogResponse)
def get_mood_icon_catalog(
    locale: str = Depends(get_locale),
) -> MoodIconCatalogResponse:
    items = [
        BuiltinMoodIconPublic(
            slug=icon.slug,
            label=resolve_label(icon.labels, locale),
            asset_path=icon.asset_path,
            default_score=icon.default_score.value if icon.default_score is not None else None,
        )
        for icon in MOOD_BUILTIN_ICONS.values()
    ]
    return MoodIconCatalogResponse(items=items)


@router.get("/icons", response_model=MoodIconListResponse)
def list_score_icons(
    score: int | None = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> MoodIconListResponse:
    try:
        icons = list_mood_icons(db, user_id=current_user.id, score=score)
    except MoodIconError as exc:
        _handle_icon_error(exc)
        raise
    return MoodIconListResponse(
        items=[_icon_meta(icon) for icon in icons],
        max_per_score=MAX_ICONS_PER_SCORE,
    )


@router.post(
    "/icons/{score}",
    status_code=status.HTTP_201_CREATED,
    response_model=MoodIconPublic,
)
async def upload_score_icon(
    score: int,
    file: UploadFile = File(),
    source: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> MoodIconPublic:
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
        icon = upload_mood_icon(
            db,
            user_id=current_user.id,
            score=score,
            data=data,
            content_type=content_type,
            original_name=original_name,
            storage=storage,
            source_data=source_data,
            source_content_type=source_content_type,
            source_original_name=source_original_name,
        )
    except MoodIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    prefs = get_or_create_preferences(db, user_id=current_user.id)
    return MoodIconPublic(
        id=icon.id,
        score=icon.score,
        mime_type=icon.mime_type,
        size_bytes=icon.size_bytes,
        original_name=icon.original_name,
        has_source=bool(icon.source_storage_key),
        preferences=MoodPreferencesPublic.model_validate(
            serialize_preferences(db, prefs, locale=locale)
        ),
    )


@router.get("/icons/id/{icon_id}")
def download_score_icon(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_mood_icon(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except MoodIconError as exc:
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
def download_score_icon_source(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        icon, data = download_mood_icon_source(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except MoodIconError as exc:
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
def delete_score_icon_by_id(
    icon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        delete_mood_icon_by_id(
            db,
            user_id=current_user.id,
            icon_id=icon_id,
            storage=storage,
        )
    except MoodIconError as exc:
        _handle_icon_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
