"""Subscription lifecycle: catalog, checkout, webhooks, cancel."""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.billing import (
    BILLING_INTERVALS,
    COMPARISON_ENTITLEMENTS,
    DEFAULT_PLAN,
    ENTITLED_SUBSCRIPTION_STATUSES,
    PLAN_CATALOG,
    BillingInterval,
    PaymentEventKind,
    PaymentKind,
    PaymentProviderId,
    PaymentStatus,
    PlanDefinition,
    PlanSlug,
    SubscriptionStatus,
    entitlements_for_plan,
    get_plan,
    plan_price,
    prices_for_plan,
)
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.payment import Payment
from app.models.payment_webhook_event import PaymentWebhookEvent
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.services.payments.base import CheckoutRequest, CheckoutSession, PaymentEvent
from app.services.payments.registry import PaymentProviderRegistry, payment_registry


class BillingError(AppError):
    pass


@dataclass(frozen=True, slots=True)
class PlanState:
    slug: str
    entitlements: frozenset[str]
    status: str | None
    billing_interval: str | None
    provider: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    is_paid: bool


@dataclass(frozen=True, slots=True)
class CheckoutResult:
    payment_id: UUID
    provider: str
    completed: bool
    checkout_url: str | None
    client_secret: str | None
    plan_slug: str
    subscription_status: str | None


def _now() -> datetime:
    return datetime.now(UTC)


def add_billing_interval(start: datetime, interval: BillingInterval | str) -> datetime:
    value = interval.value if isinstance(interval, BillingInterval) else interval
    if value == BillingInterval.YEAR.value:
        try:
            return start.replace(year=start.year + 1)
        except ValueError:
            return start.replace(year=start.year + 1, day=28)
    month = start.month + 1
    year = start.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def subscription_is_entitled(
    subscription: UserSubscription | None,
    *,
    now: datetime | None = None,
) -> bool:
    if subscription is None:
        return False
    if subscription.status not in ENTITLED_SUBSCRIPTION_STATUSES:
        return False
    moment = now or _now()
    return subscription.current_period_end >= moment


def plan_state_for_subscription(
    subscription: UserSubscription | None,
    *,
    now: datetime | None = None,
) -> PlanState:
    if subscription_is_entitled(subscription, now=now):
        assert subscription is not None
        return PlanState(
            slug=subscription.plan_slug,
            entitlements=entitlements_for_plan(subscription.plan_slug),
            status=subscription.status,
            billing_interval=subscription.billing_interval,
            provider=subscription.provider,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            is_paid=True,
        )
    return PlanState(
        slug=DEFAULT_PLAN.slug.value,
        entitlements=DEFAULT_PLAN.entitlements,
        status=None,
        billing_interval=None,
        provider=None,
        current_period_end=None,
        cancel_at_period_end=False,
        is_paid=False,
    )


def plan_state_for_user(user: User, *, now: datetime | None = None) -> PlanState:
    return plan_state_for_subscription(user.subscription, now=now)


def has_entitlement(user: User, entitlement: str, *, now: datetime | None = None) -> bool:
    return entitlement in plan_state_for_user(user, now=now).entitlements


def catalog_currency() -> str:
    return settings.billing_currency.strip().upper() or "RUB"


def serialize_plan(plan: PlanDefinition, *, currency: str) -> dict[str, object]:
    prices = [
        {
            "interval": price.interval.value,
            "amount_minor": price.amount_minor,
            "currency": price.currency,
        }
        for price in prices_for_plan(plan, currency=currency)
    ]
    return {
        "slug": plan.slug.value,
        "rank": plan.rank,
        "is_default": plan.is_default,
        "is_highlight": plan.is_highlight,
        "entitlements": sorted(plan.entitlements),
        "highlight_entitlements": list(plan.highlight_entitlements),
        "prices": prices,
    }


def catalog_payload(
    *,
    user: User | None,
    registry: PaymentProviderRegistry | None = None,
) -> dict[str, object]:
    currency = catalog_currency()
    active_registry = registry if registry is not None else payment_registry
    state = plan_state_for_user(user) if user is not None else plan_state_for_subscription(None)
    providers = [item.value for item in active_registry.public_providers()]
    return {
        "currency": currency,
        "comparison_entitlements": [item.value for item in COMPARISON_ENTITLEMENTS],
        "items": [serialize_plan(plan, currency=currency) for plan in PLAN_CATALOG],
        "providers": providers,
        "default_provider": active_registry.default_id.value,
        "current": {
            "plan_slug": state.slug,
            "status": state.status,
            "billing_interval": state.billing_interval,
            "provider": state.provider,
            "current_period_end": state.current_period_end,
            "cancel_at_period_end": state.cancel_at_period_end,
            "is_paid": state.is_paid,
            "entitlements": sorted(state.entitlements),
        },
    }


def _parse_interval(raw: str) -> BillingInterval:
    try:
        return BillingInterval(raw)
    except ValueError as exc:
        raise BillingError(
            f"Invalid billing interval: {raw}",
            code=ErrorCode.INVALID_BILLING_INTERVAL,
            status_code=400,
            params={"interval": raw},
        ) from exc


def create_checkout(
    db: Session,
    *,
    user: User,
    plan_slug: str,
    interval: str,
    provider_id: str | None = None,
    registry: PaymentProviderRegistry | None = None,
) -> CheckoutResult:
    plan = get_plan(plan_slug)
    if plan is None:
        raise BillingError(
            f"Unknown plan: {plan_slug}",
            code=ErrorCode.PLAN_NOT_FOUND,
            status_code=404,
            params={"plan": plan_slug},
        )
    if plan.is_default:
        raise BillingError(
            "The free plan cannot be purchased",
            code=ErrorCode.PLAN_NOT_PURCHASABLE,
            status_code=400,
            params={"plan": plan.slug.value},
        )
    billing_interval = _parse_interval(interval)
    price = plan_price(plan, interval=billing_interval, currency=catalog_currency())
    if price is None:
        raise BillingError(
            "No price for this plan, interval, and currency",
            code=ErrorCode.PLAN_PRICE_UNAVAILABLE,
            status_code=400,
            params={"plan": plan.slug.value, "interval": billing_interval.value},
        )
    current = plan_state_for_user(user)
    if current.slug == plan.slug.value and current.is_paid:
        raise BillingError(
            "Already on this plan",
            code=ErrorCode.ALREADY_ON_PLAN,
            status_code=409,
            params={"plan": plan.slug.value},
        )

    active_registry = registry if registry is not None else payment_registry
    provider = active_registry.get(provider_id)
    payment = Payment(
        user_id=user.id,
        plan_slug=plan.slug.value,
        billing_interval=billing_interval.value,
        provider=provider.provider_id.value,
        kind=PaymentKind.CHECKOUT.value,
        status=PaymentStatus.PENDING.value,
        amount_minor=price.amount_minor,
        currency=price.currency,
        extra={},
    )
    db.add(payment)
    db.flush()

    success_url = f"{settings.frontend_url.rstrip('/')}/plans?checkout=success"
    cancel_url = f"{settings.frontend_url.rstrip('/')}/plans?checkout=cancel"
    session = provider.create_checkout(
        CheckoutRequest(
            user_id=user.id,
            customer_email=user.email or "",
            plan_slug=plan.slug.value,
            interval=billing_interval,
            amount_minor=price.amount_minor,
            currency=price.currency,
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=str(payment.id),
            metadata={"payment_id": str(payment.id), "plan_slug": plan.slug.value},
        )
    )
    payment.provider_session_id = session.provider_session_id
    payment.provider_payment_id = session.provider_payment_id
    payment.checkout_url = session.checkout_url
    extra = dict(payment.extra or {})
    extra["provider_subscription_id"] = session.provider_subscription_id
    payment.extra = extra

    subscription_status: str | None = None
    if session.instant_complete:
        subscription = activate_subscription(db, payment=payment, session=session)
        subscription_status = subscription.status

    return CheckoutResult(
        payment_id=payment.id,
        provider=provider.provider_id.value,
        completed=session.instant_complete,
        checkout_url=session.checkout_url,
        client_secret=session.client_secret,
        plan_slug=plan.slug.value,
        subscription_status=subscription_status,
    )


def activate_subscription(
    db: Session,
    *,
    payment: Payment,
    session: CheckoutSession | None = None,
    event: PaymentEvent | None = None,
    now: datetime | None = None,
) -> UserSubscription:
    if payment.status == PaymentStatus.SUCCEEDED.value and payment.subscription_id is not None:
        existing = db.get(UserSubscription, payment.subscription_id)
        if existing is not None:
            return existing

    moment = now or _now()
    period_end = add_billing_interval(moment, payment.billing_interval)
    provider_subscription_id = None
    provider_payment_id = payment.provider_payment_id
    if session is not None:
        provider_subscription_id = session.provider_subscription_id
        provider_payment_id = session.provider_payment_id or provider_payment_id
    if event is not None:
        provider_subscription_id = event.provider_subscription_id or provider_subscription_id
        provider_payment_id = event.provider_payment_id or provider_payment_id
    extra = dict(payment.extra or {})
    stored_sub = extra.get("provider_subscription_id")
    if provider_subscription_id is None and isinstance(stored_sub, str):
        provider_subscription_id = stored_sub

    subscription = db.scalar(
        select(UserSubscription)
        .where(UserSubscription.user_id == payment.user_id)
        .with_for_update()
    )
    if subscription is None:
        subscription = UserSubscription(
            user_id=payment.user_id,
            plan_slug=payment.plan_slug,
            status=SubscriptionStatus.ACTIVE.value,
            billing_interval=payment.billing_interval,
            provider=payment.provider,
            provider_subscription_id=provider_subscription_id,
            current_period_start=moment,
            current_period_end=period_end,
            cancel_at_period_end=False,
            canceled_at=None,
        )
        db.add(subscription)
        db.flush()
    else:
        subscription.plan_slug = payment.plan_slug
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.billing_interval = payment.billing_interval
        subscription.provider = payment.provider
        subscription.provider_subscription_id = (
            provider_subscription_id or subscription.provider_subscription_id
        )
        subscription.current_period_start = moment
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None

    payment.status = PaymentStatus.SUCCEEDED.value
    payment.paid_at = event.paid_at if event is not None and event.paid_at else moment
    payment.subscription_id = subscription.id
    payment.provider_payment_id = provider_payment_id
    owner = db.get(User, payment.user_id)
    if owner is not None:
        db.expire(owner, ["subscription"])
    return subscription


def cancel_subscription(
    db: Session,
    *,
    user: User,
    registry: PaymentProviderRegistry | None = None,
) -> UserSubscription:
    subscription = user.subscription
    if subscription is None or not subscription_is_entitled(subscription):
        raise BillingError(
            "No active paid subscription",
            code=ErrorCode.NO_ACTIVE_SUBSCRIPTION,
            status_code=409,
        )
    if subscription.cancel_at_period_end:
        return subscription
    if subscription.plan_slug == PlanSlug.FREE.value:
        raise BillingError(
            "The free plan cannot be canceled",
            code=ErrorCode.SUBSCRIPTION_NOT_CANCELABLE,
            status_code=400,
        )

    if subscription.provider_subscription_id:
        active_registry = registry if registry is not None else payment_registry
        provider = active_registry.get(subscription.provider)
        provider.cancel_subscription(
            provider_subscription_id=subscription.provider_subscription_id,
            at_period_end=True,
        )

    subscription.cancel_at_period_end = True
    subscription.canceled_at = _now()
    return subscription


def _find_payment_for_event(db: Session, event: PaymentEvent) -> Payment | None:
    if event.metadata.get("payment_id"):
        try:
            payment_id = UUID(event.metadata["payment_id"])
        except ValueError:
            payment_id = None
        if payment_id is not None:
            payment = db.get(Payment, payment_id)
            if payment is not None:
                return payment
    if event.provider_session_id:
        found = db.scalar(
            select(Payment).where(
                Payment.provider == event.provider.value,
                Payment.provider_session_id == event.provider_session_id,
            )
        )
        if found is not None:
            return found
    if event.provider_payment_id:
        return db.scalar(
            select(Payment).where(
                Payment.provider == event.provider.value,
                Payment.provider_payment_id == event.provider_payment_id,
            )
        )
    return None


def apply_payment_event(db: Session, event: PaymentEvent) -> None:
    if event.kind is PaymentEventKind.CHECKOUT_COMPLETED:
        payment = _find_payment_for_event(db, event)
        if payment is None:
            raise BillingError(
                "Payment not found for webhook",
                code=ErrorCode.PAYMENT_NOT_FOUND,
                status_code=404,
            )
        activate_subscription(db, payment=payment, event=event)
        return
    if event.kind is PaymentEventKind.PAYMENT_FAILED:
        payment = _find_payment_for_event(db, event)
        if payment is not None and payment.status == PaymentStatus.PENDING.value:
            payment.status = PaymentStatus.FAILED.value
        return
    if event.kind is PaymentEventKind.SUBSCRIPTION_CANCELED:
        if not event.provider_subscription_id:
            return
        subscription = db.scalar(
            select(UserSubscription).where(
                UserSubscription.provider == event.provider.value,
                UserSubscription.provider_subscription_id == event.provider_subscription_id,
            )
        )
        if subscription is None:
            return
        subscription.status = SubscriptionStatus.CANCELED.value
        subscription.cancel_at_period_end = True
        if subscription.canceled_at is None:
            subscription.canceled_at = _now()
        return
    if event.kind is PaymentEventKind.SUBSCRIPTION_RENEWED:
        if not event.provider_subscription_id:
            return
        subscription = db.scalar(
            select(UserSubscription).where(
                UserSubscription.provider == event.provider.value,
                UserSubscription.provider_subscription_id == event.provider_subscription_id,
            )
        )
        if subscription is None:
            return
        moment = event.paid_at or _now()
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.current_period_start = moment
        subscription.current_period_end = add_billing_interval(
            moment, subscription.billing_interval
        )
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None


def process_webhook(
    db: Session,
    *,
    provider_id: str,
    headers: Mapping[str, str],
    body: bytes,
    registry: PaymentProviderRegistry | None = None,
) -> int:
    active_registry = registry if registry is not None else payment_registry
    try:
        chosen = PaymentProviderId(provider_id.strip().lower())
    except ValueError as exc:
        raise BillingError(
            f"Unknown payment provider: {provider_id}",
            code=ErrorCode.PAYMENT_PROVIDER_UNKNOWN,
            status_code=400,
            params={"provider": provider_id},
        ) from exc
    provider = active_registry.get(chosen)
    events: Sequence[PaymentEvent] = provider.parse_webhook(headers=headers, body=body)
    applied = 0
    for event in events:
        existing = db.scalar(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.provider == event.provider.value,
                PaymentWebhookEvent.provider_event_id == event.provider_event_id,
            )
        )
        if existing is not None and existing.processed_at is not None:
            continue
        row = existing
        if row is None:
            row = PaymentWebhookEvent(
                provider=event.provider.value,
                provider_event_id=event.provider_event_id,
                event_type=event.kind.value,
                payload=event.raw,
            )
            db.add(row)
            db.flush()
        apply_payment_event(db, event)
        row.processed_at = _now()
        applied += 1
    return applied


def assert_interval_known(interval: str) -> None:
    if interval not in BILLING_INTERVALS:
        raise BillingError(
            f"Invalid billing interval: {interval}",
            code=ErrorCode.INVALID_BILLING_INTERVAL,
            status_code=400,
            params={"interval": interval},
        )


__all__ = [
    "BillingError",
    "CheckoutResult",
    "PlanState",
    "activate_subscription",
    "add_billing_interval",
    "assert_interval_known",
    "cancel_subscription",
    "catalog_payload",
    "create_checkout",
    "has_entitlement",
    "plan_state_for_subscription",
    "plan_state_for_user",
    "process_webhook",
    "subscription_is_entitled",
]
