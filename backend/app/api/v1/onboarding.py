from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import raise_http_error
from app.core.i18n import parse_accept_language
from app.db.session import get_db
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingCatalogResponse,
    OnboardingCompleteRequest,
    OnboardingSuggestionsRequest,
    OnboardingSuggestionsResponse,
)
from app.schemas.user import UserPublic
from app.services.onboarding_service import (
    OnboardingError,
    complete_onboarding,
    get_onboarding_catalog_payload,
    get_onboarding_suggestions_payload,
)
from app.services.user_public import to_user_public

router = APIRouter(tags=["onboarding"])


def _to_user_public(user: User) -> UserPublic:
    return to_user_public(user)


def _locale(request: Request) -> str:
    return parse_accept_language(request.headers.get("Accept-Language"))


@router.get("/catalog", response_model=OnboardingCatalogResponse)
def onboarding_catalog(request: Request) -> OnboardingCatalogResponse:
    payload = get_onboarding_catalog_payload(locale=_locale(request))
    return OnboardingCatalogResponse.model_validate(payload)


@router.post("/suggestions", response_model=OnboardingSuggestionsResponse)
def onboarding_suggestions(
    body: OnboardingSuggestionsRequest,
    request: Request,
) -> OnboardingSuggestionsResponse:
    try:
        payload = get_onboarding_suggestions_payload(
            option_keys=body.option_keys,
            locale=_locale(request),
        )
    except OnboardingError as exc:
        raise_http_error(exc)
        raise
    return OnboardingSuggestionsResponse.model_validate(payload)


@router.post("/complete", response_model=UserPublic)
def onboarding_complete(
    body: OnboardingCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserPublic:
    try:
        updated = complete_onboarding(
            db,
            user,
            skip=body.skip,
            option_keys=None if body.skip else body.option_keys,
            tag_group_slugs=None if body.skip else body.tag_group_slugs,
            note_template_slugs=None if body.skip else body.note_template_slugs,
            email_reminders=body.email_reminders,
        )
    except OnboardingError as exc:
        raise_http_error(exc)
        raise
    return _to_user_public(updated)
