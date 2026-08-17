import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_verified_user,
    get_storage_service,
    require_telegram_bot_service,
)
from app.core.attachment_kind import AttachmentKind
from app.core.errors import raise_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.mood_entry import AttachmentPublic, MoodEntryPublic
from app.schemas.telegram import (
    TelegramBotCatalogPublic,
    TelegramBotEntryCreate,
    TelegramBotLinkRequest,
    TelegramBotMePublic,
    TelegramBotSessionPublic,
    TelegramBotSessionUpsert,
    TelegramBotUnlinkRequest,
    TelegramLinkCodeCreateResponse,
    TelegramLinkPublic,
)
from app.services.mood_entry_service import MoodEntryError, serialize_mood_entry, upload_attachment
from app.services.mood_preferences_service import (
    get_color_display_settings,
    get_score_label_overrides,
)
from app.services.storage import ObjectStorage, StorageError
from app.services.telegram_bot_service import (
    TelegramBotError,
    build_catalog,
    create_entry_for_telegram_user,
    delete_session,
    get_session,
    require_linked_user,
    resolve_bot_locale,
    serialize_session,
    upsert_session,
)
from app.services.telegram_link_service import (
    TelegramLinkError,
    create_link_code,
    get_user_by_telegram_id,
    link_telegram_account,
    serialize_link_status,
    unlink_by_telegram_user_id,
    unlink_telegram_account,
)

router = APIRouter(tags=["telegram"])
bot_router = APIRouter(
    prefix="/bot",
    tags=["telegram-bot"],
    dependencies=[Depends(require_telegram_bot_service)],
)


def _handle_bot_error(exc: TelegramBotError) -> None:
    raise_http_error(exc)


def _handle_mood_error(exc: MoodEntryError) -> None:
    raise_http_error(exc)


def _handle_storage_error(exc: StorageError) -> None:
    raise_http_error(exc)


@router.get("/link", response_model=TelegramLinkPublic)
def get_telegram_link(
    current_user: User = Depends(get_current_verified_user),
) -> TelegramLinkPublic:
    return TelegramLinkPublic.model_validate(serialize_link_status(current_user))


@router.post("/link-codes", response_model=TelegramLinkCodeCreateResponse)
def create_telegram_link_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> TelegramLinkCodeCreateResponse:
    try:
        raw_code, row, deep_link = create_link_code(db, user=current_user)
    except TelegramLinkError as exc:
        raise_http_error(exc)
    return TelegramLinkCodeCreateResponse(
        code=raw_code,
        expires_at=row.expires_at,
        deep_link=deep_link,
    )


@router.delete("/link", response_model=TelegramLinkPublic)
def delete_telegram_link(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> TelegramLinkPublic:
    try:
        user = unlink_telegram_account(db, user=current_user)
    except TelegramLinkError as exc:
        raise_http_error(exc)
    return TelegramLinkPublic.model_validate(serialize_link_status(user))


@bot_router.post("/link", response_model=TelegramBotMePublic)
def bot_link_telegram(
    body: TelegramBotLinkRequest,
    db: Session = Depends(get_db),
) -> TelegramBotMePublic:
    try:
        user = link_telegram_account(
            db,
            code=body.code,
            telegram_user_id=body.telegram_user_id,
            telegram_chat_id=body.telegram_chat_id,
            locale=body.locale,
        )
    except TelegramLinkError as exc:
        raise_http_error(exc)
    return TelegramBotMePublic(
        linked=True,
        user_id=str(user.id),
        email=user.email,
        timezone=user.timezone,
        locale=user.telegram_locale,
    )


@bot_router.post("/unlink", response_model=TelegramBotMePublic)
def bot_unlink_telegram(
    body: TelegramBotUnlinkRequest,
    db: Session = Depends(get_db),
) -> TelegramBotMePublic:
    try:
        unlink_by_telegram_user_id(db, telegram_user_id=body.telegram_user_id)
    except TelegramLinkError as exc:
        raise_http_error(exc)
    return TelegramBotMePublic(linked=False)


@bot_router.get("/me", response_model=TelegramBotMePublic)
def bot_me(
    telegram_user_id: int,
    db: Session = Depends(get_db),
) -> TelegramBotMePublic:
    user = get_user_by_telegram_id(db, telegram_user_id=telegram_user_id)
    if user is None:
        return TelegramBotMePublic(linked=False)
    return TelegramBotMePublic(
        linked=True,
        user_id=str(user.id),
        email=user.email,
        timezone=user.timezone,
        locale=user.telegram_locale,
    )


@bot_router.get("/catalog", response_model=TelegramBotCatalogPublic)
def bot_catalog(
    telegram_user_id: int = Query(gt=0),
    locale: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TelegramBotCatalogPublic:
    try:
        user = require_linked_user(db, telegram_user_id=telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    payload = build_catalog(db, user=user, locale=locale)
    return TelegramBotCatalogPublic.model_validate(payload)


@bot_router.post(
    "/entries",
    status_code=status.HTTP_201_CREATED,
    response_model=MoodEntryPublic,
)
def bot_create_entry(
    body: TelegramBotEntryCreate,
    db: Session = Depends(get_db),
) -> MoodEntryPublic:
    try:
        user = require_linked_user(db, telegram_user_id=body.telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    try:
        entry = create_entry_for_telegram_user(
            db,
            user=user,
            score=body.score,
            tag_ids=body.tag_ids,
            goal_ids=body.goal_ids,
            note=body.note,
            source=body.source,
        )
    except MoodEntryError as exc:
        _handle_mood_error(exc)
        raise
    locale = resolve_bot_locale(user)
    label_overrides = get_score_label_overrides(db, user_id=user.id)
    return MoodEntryPublic.model_validate(
        serialize_mood_entry(
            entry,
            locale=locale,
            label_overrides=label_overrides,
            color_settings=get_color_display_settings(db, user_id=user.id),
        )
    )


@bot_router.post(
    "/entries/{entry_id}/attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=AttachmentPublic,
)
async def bot_upload_attachment(
    entry_id: uuid.UUID,
    telegram_user_id: Annotated[int, Form(gt=0)],
    kind: Annotated[AttachmentKind, Form()],
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage_service),
) -> AttachmentPublic:
    try:
        user = require_linked_user(db, telegram_user_id=telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    data = await file.read()
    original_name = file.filename or "file"
    content_type = file.content_type or "application/octet-stream"
    try:
        attachment = upload_attachment(
            db,
            user_id=user.id,
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
        transcription=attachment.transcription,
    )


@bot_router.get("/sessions/{telegram_user_id}", response_model=TelegramBotSessionPublic)
def bot_get_session(
    telegram_user_id: int,
    db: Session = Depends(get_db),
) -> TelegramBotSessionPublic:
    try:
        require_linked_user(db, telegram_user_id=telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    row = get_session(db, telegram_user_id=telegram_user_id)
    return TelegramBotSessionPublic.model_validate(
        serialize_session(row, telegram_user_id=telegram_user_id)
    )


@bot_router.put("/sessions/{telegram_user_id}", response_model=TelegramBotSessionPublic)
def bot_upsert_session(
    telegram_user_id: int,
    body: TelegramBotSessionUpsert,
    db: Session = Depends(get_db),
) -> TelegramBotSessionPublic:
    try:
        require_linked_user(db, telegram_user_id=telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    row = upsert_session(db, telegram_user_id=telegram_user_id, state=body.state)
    return TelegramBotSessionPublic.model_validate(
        serialize_session(row, telegram_user_id=telegram_user_id)
    )


@bot_router.delete("/sessions/{telegram_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def bot_delete_session(
    telegram_user_id: int,
    db: Session = Depends(get_db),
) -> None:
    try:
        require_linked_user(db, telegram_user_id=telegram_user_id)
    except TelegramBotError as exc:
        _handle_bot_error(exc)
        raise
    delete_session(db, telegram_user_id=telegram_user_id)


router.include_router(bot_router)
