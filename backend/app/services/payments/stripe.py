"""Stripe Checkout + Billing adapter (scaffold).

When ``STRIPE_SECRET_KEY`` is set, ``checkout_payload`` is the body we will
POST to Stripe Checkout Sessions. Wire ``httpx`` / the Stripe SDK in
``create_checkout`` when going live — do not change the billing service.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.billing import BillingInterval, PaymentProviderId
from app.core.error_codes import ErrorCode
from app.services.payments.base import (
    BasePaymentProvider,
    CheckoutRequest,
    CheckoutSession,
    PaymentError,
    PaymentEvent,
)


class StripePaymentProvider(BasePaymentProvider):
    """Stripe adapter. Hidden until secret + webhook keys are configured."""

    def __init__(self, *, secret_key: str = "", webhook_secret: str = "") -> None:
        self._secret_key = secret_key.strip()
        self._webhook_secret = webhook_secret.strip()

    @property
    def provider_id(self) -> PaymentProviderId:
        return PaymentProviderId.STRIPE

    def is_configured(self) -> bool:
        return bool(self._secret_key and self._webhook_secret)

    def checkout_payload(self, request: CheckoutRequest) -> dict[str, object]:
        """Checkout Session parameters for Stripe's API (mode=subscription)."""
        interval = "month" if request.interval is BillingInterval.MONTH else "year"
        return {
            "mode": "subscription",
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "customer_email": request.customer_email,
            "client_reference_id": str(request.user_id),
            "metadata": {
                "user_id": str(request.user_id),
                "plan_slug": request.plan_slug,
                **request.metadata,
            },
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": request.currency.lower(),
                        "unit_amount": request.amount_minor,
                        "recurring": {"interval": interval},
                        "product_data": {
                            "name": f"GlowPath {request.plan_slug}",
                            "metadata": {"plan_slug": request.plan_slug},
                        },
                    },
                }
            ],
        }

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        if not self.is_configured():
            raise PaymentError(
                "Stripe is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        del request
        raise PaymentError(
            "Stripe checkout is not wired yet",
            code=ErrorCode.PAYMENT_PROVIDER_NOT_READY,
            status_code=501,
            params={"provider": self.provider_id.value},
        )

    def parse_webhook(
        self,
        *,
        headers: Mapping[str, str],
        body: bytes,
    ) -> Sequence[PaymentEvent]:
        del headers, body
        if not self.is_configured():
            raise PaymentError(
                "Stripe is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        raise PaymentError(
            "Stripe webhooks are not wired yet",
            code=ErrorCode.PAYMENT_PROVIDER_NOT_READY,
            status_code=501,
            params={"provider": self.provider_id.value},
        )

    def cancel_subscription(
        self,
        *,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> None:
        del provider_subscription_id, at_period_end
        if not self.is_configured():
            raise PaymentError(
                "Stripe is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        raise PaymentError(
            "Stripe cancel is not wired yet",
            code=ErrorCode.PAYMENT_PROVIDER_NOT_READY,
            status_code=501,
            params={"provider": self.provider_id.value},
        )
