import uuid
from datetime import datetime
from typing import Annotated, TypedDict
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.core.attachment_kind import AttachmentKind
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.schemas.mood_entry import (
    AttachmentPublic,
    AttachmentReorderRequest,
    GalleryPhotoListResponse,
    GalleryPhotoPublic,
    MoodEntryCalendarResponse,
    MoodEntryCreate,
    MoodEntryListResponse,
    MoodEntryPatch,
    MoodEntryPublic,
    MoodEntryStatsResponse,
    MoodEntryStreakResponse,
    MoodInsightsResponse,
)
from app.services.mood_entry_service import (
    MoodEntryError,
    create_mood_entry,
    delete_attachment,
    delete_mood_entry,
    download_attachment,
    get_mood_entry,
    get_mood_entry_calendar,
    get_mood_entry_stats,
    get_mood_entry_streak,
    list_gallery_photos,
    list_mood_entries,
    patch_mood_entry,
    reorder_photo_attachments,
    search_mood_entries,
    serialize_mood_entry,
    upload_attachment,
)
from app.services.mood_insight_service import get_mood_insights
from app.services.mood_preferences_service import (
    ColorDisplaySettings,
    get_color_display_settings,
    get_score_label_overrides,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["mood-entries"])


def _handle_mood_error(exc: MoodEntryError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


def _to_public(
    entry: MoodEntry,
    *,
    locale: str,
    label_overrides: dict[str, str] | None = None,
    color_settings: ColorDisplaySettings | None = None,
    unlocked_achievements: list[dict] | None = None,
) -> MoodEntryPublic:
    payload = serialize_mood_entry(
        entry,
        locale=locale,
        label_overrides=label_overrides,
        color_settings=color_settings,
    )
    if unlocked_achievements:
        payload["unlocked_achievements"] = unlocked_achievements
    return MoodEntryPublic.model_validate(payload)


class _EntryView(TypedDict):
    label_overrides: dict[str, str]
    color_settings: ColorDisplaySettings


def _entry_view_kwargs(db: Session, user_id: uuid.UUID) -> _EntryView:
    return {
        "label_overrides": get_score_label_overrides(db, user_id=user_id),
        "color_settings": get_color_display_settings(db, user_id=user_id),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MoodEntryPublic)
def create_entry(
    body: MoodEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodEntryPublic:
    try:
        entry, unlocked = create_mood_entry(
            db,
            user_id=current_user.id,
            score=body.score,
            recorded_at=body.recorded_at,
            note=body.note,
            tag_ids=body.tag_ids,
            goal_ids=body.goal_ids,
            goal_progress=body.goal_progress,
            source=body.source,
            locale=locale,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return _to_public(
        entry,
        locale=locale,
        unlocked_achievements=unlocked,
        **_entry_view_kwargs(db, current_user.id),
    )


@router.get("", response_model=MoodEntryListResponse)
def list_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    recorded_from: Annotated[datetime | None, Query()] = None,
    recorded_to: Annotated[datetime | None, Query()] = None,
    is_favorite: Annotated[bool | None, Query()] = None,
) -> MoodEntryListResponse:
    entries = list_mood_entries(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
        is_favorite=is_favorite,
    )
    view = _entry_view_kwargs(db, current_user.id)
    return MoodEntryListResponse(
        items=[_to_public(entry, locale=locale, **view) for entry in entries],
        limit=limit,
        offset=offset,
    )


@router.get("/calendar", response_model=MoodEntryCalendarResponse)
def calendar_entries(
    recorded_from: Annotated[datetime, Query()],
    recorded_to: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> MoodEntryCalendarResponse:
    try:
        days = get_mood_entry_calendar(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return MoodEntryCalendarResponse.model_validate({"days": days})


@router.get("/streak", response_model=MoodEntryStreakResponse)
def streak_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> MoodEntryStreakResponse:
    try:
        payload = get_mood_entry_streak(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return MoodEntryStreakResponse.model_validate(payload)


@router.get("/stats", response_model=MoodEntryStatsResponse)
def stats_entries(
    recorded_from: Annotated[datetime, Query()],
    recorded_to: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodEntryStatsResponse:
    try:
        payload = get_mood_entry_stats(
            db,
            user_id=current_user.id,
            timezone_name=current_user.timezone,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
            locale=locale,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return MoodEntryStatsResponse.model_validate(payload)


@router.get("/insights", response_model=MoodInsightsResponse)
def insight_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
    recorded_from: Annotated[datetime | None, Query()] = None,
    recorded_to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=8)] = 4,
    focus_entry_id: Annotated[uuid.UUID | None, Query()] = None,
) -> MoodInsightsResponse:
    """Pattern cards over mood × weekday × time of day × tags.

    Omit ``recorded_from`` / ``recorded_to`` to use the rolling 8-week window.
    ``focus_entry_id`` only reorders already-qualified cards (post-save).
    """
    try:
        payload = get_mood_insights(
            db,
            user=current_user,
            locale=locale,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
            limit=limit,
            focus_entry_id=focus_entry_id,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return MoodInsightsResponse.model_validate(payload)


@router.get("/search", response_model=MoodEntryListResponse)
def search_entries(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MoodEntryListResponse:
    try:
        entries = search_mood_entries(
            db,
            user_id=current_user.id,
            query=q,
            limit=limit,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    view = _entry_view_kwargs(db, current_user.id)
    return MoodEntryListResponse(
        items=[_to_public(entry, locale=locale, **view) for entry in entries],
        limit=limit,
        offset=0,
    )


@router.get("/photos", response_model=GalleryPhotoListResponse)
def list_photos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    limit: Annotated[int, Query(ge=1, le=100)] = 48,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GalleryPhotoListResponse:
    photos = list_gallery_photos(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return GalleryPhotoListResponse(
        items=[
            GalleryPhotoPublic(
                id=photo.id,
                mood_entry_id=photo.mood_entry_id,
                original_name=photo.original_name,
                mime_type=photo.mime_type,
                created_at=photo.created_at,
            )
            for photo in photos
        ],
        limit=limit,
        offset=offset,
    )


@router.get("/{entry_id}", response_model=MoodEntryPublic)
def get_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodEntryPublic:
    try:
        entry = get_mood_entry(db, user_id=current_user.id, entry_id=entry_id)
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return _to_public(entry, locale=locale, **_entry_view_kwargs(db, current_user.id))


@router.patch("/{entry_id}", response_model=MoodEntryPublic)
def patch_entry(
    entry_id: uuid.UUID,
    body: MoodEntryPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodEntryPublic:
    fields = body.model_dump(exclude_unset=True)
    try:
        entry, unlocked = patch_mood_entry(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            fields=fields,
            locale=locale,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return _to_public(
        entry,
        locale=locale,
        unlocked_achievements=unlocked,
        **_entry_view_kwargs(db, current_user.id),
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        delete_mood_entry(db, user_id=current_user.id, entry_id=entry_id, storage=storage)
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{entry_id}/attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=AttachmentPublic,
)
async def create_attachment(
    entry_id: uuid.UUID,
    kind: Annotated[AttachmentKind, Form()],
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
    locale: str = Depends(get_locale),
) -> AttachmentPublic:
    data = await file.read()
    original_name = file.filename or "file"
    content_type = file.content_type or "application/octet-stream"
    try:
        attachment = upload_attachment(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            kind=kind,
            data=data,
            content_type=content_type,
            original_name=original_name,
            storage=storage,
            locale=locale,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise
    return AttachmentPublic(
        id=attachment.id,
        kind=attachment.kind,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        original_name=attachment.original_name,
        position=attachment.position,
        transcription=attachment.transcription,
    )


@router.put(
    "/{entry_id}/attachments/reorder",
    response_model=list[AttachmentPublic],
)
def reorder_entry_photo_attachments(
    entry_id: uuid.UUID,
    body: AttachmentReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> list[AttachmentPublic]:
    try:
        photos = reorder_photo_attachments(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            ordered_ids=body.ordered_ids,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return [
        AttachmentPublic(
            id=attachment.id,
            kind=attachment.kind,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            original_name=attachment.original_name,
            position=attachment.position,
            transcription=attachment.transcription,
        )
        for attachment in photos
    ]


@router.get("/{entry_id}/attachments/{attachment_id}")
def download_entry_attachment(
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> FastAPIResponse:
    try:
        attachment, data = download_attachment(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            attachment_id=attachment_id,
            storage=storage,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    except StorageError as exc:
        _handle_storage_error(exc)
        raise

    filename = quote(attachment.original_name)
    return FastAPIResponse(
        content=data,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
        },
    )


@router.delete(
    "/{entry_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_entry_attachment(
    entry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> Response:
    try:
        delete_attachment(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            attachment_id=attachment_id,
            storage=storage,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
