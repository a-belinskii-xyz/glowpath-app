from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_optional_current_user
from app.core.error_codes import ErrorCode
from app.core.errors import raise_http_error, structured_detail
from app.core.feature_flags import FeatureFlag, is_feature_enabled_for_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import (
    CheckoutRequestBody,
    CheckoutResponse,
    CurrentSubscriptionPublic,
    PlanCatalogResponse,
    WebhookAcceptedResponse,
)
from app.services.billing_service import (
    BillingError,
    PlanState,
    cancel_subscription,
    catalog_payload,
    create_checkout,
    plan_state_for_user,
    process_webhook,
)
from app.services.payments.base import PaymentError

router = APIRouter(tags=["billing"])


def _require_billing(user: User | None) -> None:
    """Plans and checkout are visible only to allowlisted testers (GP-15)."""
    if user is None or not is_feature_enabled_for_user(FeatureFlag.BILLING, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=structured_detail(
                code=ErrorCode.BILLING_DISABLED,
                message="Plans are not enabled for this user",
            ),
        )


def _handle_billing_error(exc: BillingError | PaymentError) -> None:
    raise_http_error(exc)
    raise RuntimeError("unreachable")


def _subscription_public(state: PlanState) -> CurrentSubscriptionPublic:
    return CurrentSubscriptionPublic.model_validate(
        {
            "plan_slug": state.slug,
            "status": state.status,
            "billing_interval": state.billing_interval,
            "provider": state.provider,
            "current_period_end": state.current_period_end,
            "cancel_at_period_end": state.cancel_at_period_end,
            "is_paid": state.is_paid,
            "entitlements": sorted(state.entitlements),
        }
    )


@router.get("/plans", response_model=PlanCatalogResponse)
def list_plans(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> PlanCatalogResponse:
    del db
    _require_billing(current_user)
    return PlanCatalogResponse.model_validate(catalog_payload(user=current_user))


@router.get("/subscription", response_model=CurrentSubscriptionPublic)
def get_subscription(
    current_user: User = Depends(get_current_verified_user),
) -> CurrentSubscriptionPublic:
    _require_billing(current_user)
    return _subscription_public(plan_state_for_user(current_user))


@router.post("/checkout", response_model=CheckoutResponse)
def start_checkout(
    body: CheckoutRequestBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> CheckoutResponse:
    _require_billing(current_user)
    try:
        result = create_checkout(
            db,
            user=current_user,
            plan_slug=body.plan_slug.value,
            interval=body.interval.value,
            provider_id=body.provider.value if body.provider else None,
        )
    except (BillingError, PaymentError) as exc:
        db.rollback()
        _handle_billing_error(exc)
    db.commit()
    return CheckoutResponse.model_validate(
        {
            "payment_id": result.payment_id,
            "provider": result.provider,
            "completed": result.completed,
            "checkout_url": result.checkout_url,
            "client_secret": result.client_secret,
            "plan_slug": result.plan_slug,
            "subscription_status": result.subscription_status,
        }
    )


@router.post("/cancel", response_model=CurrentSubscriptionPublic)
def cancel_current_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> CurrentSubscriptionPublic:
    _require_billing(current_user)
    try:
        cancel_subscription(db, user=current_user)
    except (BillingError, PaymentError) as exc:
        db.rollback()
        _handle_billing_error(exc)
    db.commit()
    db.refresh(current_user)
    return _subscription_public(plan_state_for_user(current_user))


@router.post(
    "/webhooks/{provider_id}",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_200_OK,
)
async def billing_webhook(
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> WebhookAcceptedResponse:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        applied = process_webhook(db, provider_id=provider_id, headers=headers, body=body)
    except (BillingError, PaymentError) as exc:
        db.rollback()
        _handle_billing_error(exc)
    db.commit()
    return WebhookAcceptedResponse(applied=applied)
