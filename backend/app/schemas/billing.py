from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.billing import BillingInterval, PaymentProviderId, PlanSlug


class PlanPricePublic(BaseModel):
    interval: BillingInterval
    amount_minor: int
    currency: str


class PlanPublic(BaseModel):
    slug: PlanSlug
    rank: int
    is_default: bool
    is_highlight: bool
    entitlements: list[str]
    highlight_entitlements: list[str]
    prices: list[PlanPricePublic]


class CurrentSubscriptionPublic(BaseModel):
    plan_slug: PlanSlug
    status: str | None = None
    billing_interval: BillingInterval | None = None
    provider: PaymentProviderId | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    is_paid: bool = False
    entitlements: list[str] = Field(default_factory=list)


class PlanCatalogResponse(BaseModel):
    currency: str
    comparison_entitlements: list[str]
    items: list[PlanPublic]
    providers: list[PaymentProviderId]
    default_provider: PaymentProviderId
    current: CurrentSubscriptionPublic


class CheckoutRequestBody(BaseModel):
    plan_slug: PlanSlug
    interval: BillingInterval
    provider: PaymentProviderId | None = None


class CheckoutResponse(BaseModel):
    payment_id: UUID
    provider: PaymentProviderId
    completed: bool
    checkout_url: str | None = None
    client_secret: str | None = None
    plan_slug: PlanSlug
    subscription_status: str | None = None


class WebhookAcceptedResponse(BaseModel):
    accepted: bool = True
    applied: int = 0
