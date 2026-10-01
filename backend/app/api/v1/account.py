import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_locale, get_storage_service
from app.core.error_codes import ErrorCode
from app.core.errors import AppError, raise_http_error, structured_detail
from app.db.session import get_db
from app.models.diary_restore import DiaryRestore
from app.models.user import User
from app.schemas.account import (
    AccountDeleteRequest,
    AccountExportTelegramResponse,
    DiaryRestorePublic,
    RestoreSummary,
    RestoreWarning,
)
from app.services.account_deletion_service import delete_account
from app.services.account_export_service import (
    build_account_export,
    export_filename,
    iter_file,
    send_account_export_to_telegram,
)
from app.services.diary_archive.restore import (
    add_restore_parts,
    apply_restore,
    cancel_restore,
    create_restore,
)
from app.services.storage import ObjectStorage
from app.services.telegram_delivery import TelegramDeliveryError

router = APIRouter(tags=["account"])


@router.get("/export")
def get_account_export(
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> StreamingResponse:
    archive = build_account_export(db, user=current_user, storage=storage, locale=locale)
    return StreamingResponse(
        iter_file(archive),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{export_filename()}"'},
    )


@router.post("/export/telegram", response_model=AccountExportTelegramResponse)
def post_account_export_to_telegram(
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> AccountExportTelegramResponse:
    """Bot sends the export ZIP (split into parts under 50 MB) to the user's Telegram chat."""
    try:
        parts = send_account_export_to_telegram(
            db, user=current_user, storage=storage, locale=locale
        )
    except TelegramDeliveryError as exc:
        raise_http_error(exc)
    return AccountExportTelegramResponse(parts=parts)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_account(
    body: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> None:
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=structured_detail(
                code=ErrorCode.ACCOUNT_DELETE_NOT_CONFIRMED,
                message="Account deletion must be confirmed",
            ),
        )
    delete_account(db, user=current_user, storage=storage)


def _restore_public(restore: DiaryRestore) -> DiaryRestorePublic:
    return DiaryRestorePublic(
        id=restore.id,
        status=restore.status,
        format_version=restore.format_version,
        exported_at=restore.archive_exported_at,
        created_at=restore.created_at,
        applied_at=restore.applied_at,
        summary=RestoreSummary.model_validate(restore.summary),
        warnings=[RestoreWarning.model_validate(item) for item in restore.warnings],
    )


@router.post("/restores", response_model=DiaryRestorePublic, status_code=status.HTTP_201_CREATED)
def post_restore(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> DiaryRestorePublic:
    """Upload export ZIP part(s) and get a preview; the diary does not change yet."""
    try:
        restore = create_restore(
            db, user=current_user, storage=storage, files=[item.file for item in files]
        )
    except AppError as exc:
        raise_http_error(exc)
    return _restore_public(restore)


@router.post("/restores/{restore_id}/parts", response_model=DiaryRestorePublic)
def post_restore_parts(
    restore_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> DiaryRestorePublic:
    try:
        restore = add_restore_parts(
            db,
            user=current_user,
            storage=storage,
            restore_id=restore_id,
            files=[item.file for item in files],
        )
    except AppError as exc:
        raise_http_error(exc)
    return _restore_public(restore)


@router.post("/restores/{restore_id}/apply", response_model=DiaryRestorePublic)
def post_restore_apply(
    restore_id: uuid.UUID,
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> DiaryRestorePublic:
    """Merge the previewed archive into the diary; existing entries stay untouched."""
    try:
        restore = apply_restore(
            db, user=current_user, storage=storage, restore_id=restore_id, locale=locale
        )
    except AppError as exc:
        raise_http_error(exc)
    return _restore_public(restore)


@router.post("/restores/{restore_id}/cancel", response_model=DiaryRestorePublic)
def post_restore_cancel(
    restore_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStorage = Depends(get_storage_service),
) -> DiaryRestorePublic:
    try:
        restore = cancel_restore(db, user=current_user, storage=storage, restore_id=restore_id)
    except AppError as exc:
        raise_http_error(exc)
    return _restore_public(restore)
