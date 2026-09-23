"""Payment provider contract.

New processors (Stripe, Sber, YooKassa, …) subclass ``BasePaymentProvider``.
The billing service never talks to a PSP directly — only through this ABC.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.billing import BillingInterval, PaymentEventKind, PaymentProviderId
from app.core.errors import AppError


class PaymentError(AppError):
    pass


@dataclass(frozen=True, slots=True)
class CheckoutRequest:
    """Provider-agnostic checkout input."""

    user_id: UUID
    customer_email: str
    plan_slug: str
    interval: BillingInterval
    amount_minor: int
    currency: str
    success_url: str
    cancel_url: str
    idempotency_key: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    """Result of starting a checkout with a provider.

    ``instant_complete`` is for local/test providers that settle in-process.
    Live PSPs return a ``checkout_url`` (or ``client_secret``) instead.
    """

    provider: PaymentProviderId
    provider_session_id: str
    checkout_url: str | None = None
    client_secret: str | None = None
    provider_subscription_id: str | None = None
    provider_payment_id: str | None = None
    instant_complete: bool = False
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """Normalized webhook / async event from any provider."""

    provider: PaymentProviderId
    provider_event_id: str
    kind: PaymentEventKind
    provider_session_id: str | None = None
    provider_payment_id: str | None = None
    provider_subscription_id: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    paid_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class BasePaymentProvider:
    """Abstract payment processor.

    Subclasses must set ``provider_id`` and implement ``create_checkout``,
    ``parse_webhook``, and ``cancel_subscription``.
    """

    @property
    def provider_id(self) -> PaymentProviderId:
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Whether credentials are present. Unconfigured providers stay hidden."""
        return True

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        raise NotImplementedError

    def parse_webhook(
        self,
        *,
        headers: Mapping[str, str],
        body: bytes,
    ) -> Sequence[PaymentEvent]:
        raise NotImplementedError

    def cancel_subscription(
        self,
        *,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> None:
        raise NotImplementedError
