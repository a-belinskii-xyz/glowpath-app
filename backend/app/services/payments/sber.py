"""Sber Pay / Sberbank acquiring adapter (scaffold).

Same contract as Stripe. Fill in register + status callbacks when connecting
Sber's payment API; keep metadata (user_id, plan_slug, payment_id) on the order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.billing import PaymentProviderId
from app.core.error_codes import ErrorCode
from app.services.payments.base import (
    BasePaymentProvider,
    CheckoutRequest,
    CheckoutSession,
    PaymentError,
    PaymentEvent,
)


class SberPaymentProvider(BasePaymentProvider):
    """Sber adapter. Hidden until API user + secret are configured."""

    def __init__(self, *, username: str = "", password: str = "") -> None:
        self._username = username.strip()
        self._password = password.strip()

    @property
    def provider_id(self) -> PaymentProviderId:
        return PaymentProviderId.SBER

    def is_configured(self) -> bool:
        return bool(self._username and self._password)

    def register_order_payload(self, request: CheckoutRequest) -> dict[str, object]:
        """Body for Sber ``register.do`` (amount in minor units)."""
        return {
            "orderNumber": request.idempotency_key,
            "amount": request.amount_minor,
            "currency": "643" if request.currency.upper() == "RUB" else request.currency,
            "returnUrl": request.success_url,
            "failUrl": request.cancel_url,
            "email": request.customer_email,
            "description": f"GlowPath {request.plan_slug} ({request.interval.value})",
            "jsonParams": {
                "user_id": str(request.user_id),
                "plan_slug": request.plan_slug,
                **request.metadata,
            },
        }

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        if not self.is_configured():
            raise PaymentError(
                "Sber Pay is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        del request
        raise PaymentError(
            "Sber Pay checkout is not wired yet",
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
                "Sber Pay is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        raise PaymentError(
            "Sber Pay callbacks are not wired yet",
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
                "Sber Pay is not configured",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": self.provider_id.value},
            )
        raise PaymentError(
            "Sber Pay cancel is not wired yet",
            code=ErrorCode.PAYMENT_PROVIDER_NOT_READY,
            status_code=501,
            params={"provider": self.provider_id.value},
        )
