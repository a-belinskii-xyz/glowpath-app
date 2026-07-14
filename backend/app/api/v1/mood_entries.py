import uuid
from datetime import datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_locale, get_storage_service
from app.core.attachment_kind import AttachmentKind
from app.db.session import get_db
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.schemas.mood_entry import (
    AttachmentPublic,
    MoodEntryCalendarResponse,
    MoodEntryCreate,
    MoodEntryListResponse,
    MoodEntryPatch,
    MoodEntryPublic,
)
from app.services.mood_entry_service import (
    MoodEntryError,
    create_mood_entry,
    delete_attachment,
    delete_mood_entry,
    download_attachment,
    get_mood_entry,
    get_mood_entry_calendar,
    list_mood_entries,
    patch_mood_entry,
    serialize_mood_entry,
    upload_attachment,
)
from app.services.storage import ObjectStorage, StorageError

router = APIRouter(tags=["mood-entries"])


def _handle_mood_error(exc: MoodEntryError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _handle_storage_error(exc: StorageError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _to_public(entry: MoodEntry, *, locale: str) -> MoodEntryPublic:
    return MoodEntryPublic.model_validate(serialize_mood_entry(entry, locale=locale))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MoodEntryPublic)
def create_entry(
    body: MoodEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
) -> MoodEntryPublic:
    try:
        entry = create_mood_entry(
            db,
            user_id=current_user.id,
            score=body.score,
            recorded_at=body.recorded_at,
            note=body.note,
            tag_ids=body.tag_ids,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return _to_public(entry, locale=locale)


@router.get("", response_model=MoodEntryListResponse)
def list_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    locale: str = Depends(get_locale),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    recorded_from: Annotated[datetime | None, Query()] = None,
    recorded_to: Annotated[datetime | None, Query()] = None,
) -> MoodEntryListResponse:
    entries = list_mood_entries(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )
    return MoodEntryListResponse(
        items=[_to_public(entry, locale=locale) for entry in entries],
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
    return _to_public(entry, locale=locale)


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
        entry = patch_mood_entry(
            db,
            user_id=current_user.id,
            entry_id=entry_id,
            fields=fields,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    return _to_public(entry, locale=locale)


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
    )


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
