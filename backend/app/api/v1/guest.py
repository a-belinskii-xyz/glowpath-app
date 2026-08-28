from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.db.session import get_db
from app.models.user import User
from app.schemas.guest import (
    GuestExperimentSummaryResponse,
    GuestHeartbeatRequest,
    GuestHeartbeatResponse,
    GuestImportRequest,
    GuestImportResponse,
)
from app.services.guest_import_service import GuestImportError, import_guest_diary
from app.services.visitor_experiment_service import (
    get_experiment_summary,
    record_guest_heartbeat,
)

router = APIRouter(tags=["guest"])


@router.post("/heartbeat", response_model=GuestHeartbeatResponse)
def guest_heartbeat(
    body: GuestHeartbeatRequest,
    db: Session = Depends(get_db),
) -> GuestHeartbeatResponse:
    try:
        record_guest_heartbeat(
            db,
            visitor_id=body.visitor_id,
            timezone=body.timezone,
            locale=body.locale,
            entry_count=body.entry_count,
            onboarding_completed=body.onboarding_completed,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "not_in_treatment":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=structured_detail(
                    code=ErrorCode.GUEST_NOT_IN_TREATMENT,
                    message="Guest heartbeat is only allowed for treatment visitors",
                ),
            ) from exc
        if code == "feature_disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=structured_detail(
                    code=ErrorCode.GUEST_FEATURE_DISABLED,
                    message="Guest local diary experiment is disabled",
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=structured_detail(code=ErrorCode.USER_NOT_FOUND, message="Visitor not found"),
        ) from exc
    return GuestHeartbeatResponse()


@router.post("/import", response_model=GuestImportResponse)
def guest_import(
    body: GuestImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GuestImportResponse:
    try:
        result = import_guest_diary(
            db,
            user=user,
            visitor_id=body.visitor_id,
            payload=body.payload,
        )
    except GuestImportError as exc:
        raise_http_error(exc)
        raise
    return GuestImportResponse(
        imported_entries=result["imported_entries"],
        skipped=result["skipped"],
    )


@router.get("/experiment/summary", response_model=GuestExperimentSummaryResponse)
def guest_experiment_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GuestExperimentSummaryResponse:
    if not user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(code=ErrorCode.NOT_AUTHENTICATED, message="Staff only"),
        )
    summary = get_experiment_summary(db)
    return GuestExperimentSummaryResponse(
        control_visitors=summary.control_visitors,
        treatment_visitors=summary.treatment_visitors,
        treatment_active_7d=summary.treatment_active_7d,
        control_converted=summary.control_converted,
        treatment_converted=summary.treatment_converted,
        treatment_median_entry_count_on_convert=summary.treatment_median_entry_count_on_convert,
        treatment_existing_login_skipped=summary.treatment_existing_login_skipped,
    )
