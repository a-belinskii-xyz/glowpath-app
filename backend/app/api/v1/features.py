import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import raise_http_error
from app.core.i18n import parse_accept_language
from app.db.session import get_db
from app.schemas.features import (
    FeatureBootstrapRequest,
    FeatureBootstrapResponse,
)
from app.services.visitor_experiment_service import (
    bootstrap_visitor,
    visitor_cookie_settings,
)

router = APIRouter(tags=["features"])


def _parse_visitor_cookie(request: Request) -> uuid.UUID | None:
    raw = request.cookies.get(settings.guest_visitor_cookie_name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


@router.post("/bootstrap", response_model=FeatureBootstrapResponse)
def feature_bootstrap(
    body: FeatureBootstrapRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> FeatureBootstrapResponse:
    fingerprint_payload = body.fingerprint.model_dump() if body.fingerprint else None
    result = bootstrap_visitor(
        db,
        cookie_visitor_id=_parse_visitor_cookie(request),
        fingerprint_payload=fingerprint_payload,
        user_agent=request.headers.get("user-agent", ""),
        accept_language=parse_accept_language(request.headers.get("Accept-Language")),
    )
    cookie = visitor_cookie_settings()
    response.set_cookie(
        key=str(cookie["key"]),
        value=str(result.visitor_id),
        httponly=bool(cookie["httponly"]),
        samesite=cookie["samesite"],  # type: ignore[arg-type]
        secure=bool(cookie["secure"]),
        max_age=int(cookie["max_age"]),
        path=str(cookie["path"]),
    )
    return FeatureBootstrapResponse(
        visitor_id=str(result.visitor_id),
        guest_local_diary=result.guest_local_diary,
        cohort=result.cohort,
        features={"notifications": settings.feature_notifications_enabled},
    )
