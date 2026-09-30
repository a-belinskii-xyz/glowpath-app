from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_locale, get_storage_service
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import AccountDeleteRequest, AccountExportTelegramResponse
from app.services.account_deletion_service import delete_account
from app.services.account_export_service import (
    build_account_export,
    export_filename,
    iter_file,
    send_account_export_to_telegram,
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
