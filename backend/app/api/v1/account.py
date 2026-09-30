from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_locale, get_storage_service
from app.db.session import get_db
from app.models.user import User
from app.services.account_export_service import (
    build_account_export,
    export_filename,
    iter_file,
)
from app.services.storage import ObjectStorage

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
