"""Freemium plan catalog, entitlements, and billing constants.

Plans and prices live here so copy/limits can change without a migration.
Subscriptions and payments are stored in the database; this module is the
source of truth for *what a plan means*.

Entitlement slugs are placeholders — gate real features against
``entitlements_for_plan`` later, then adjust this catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlanSlug(StrEnum):
    FREE = "free"
    PLUS = "plus"
    PRO = "pro"


class BillingInterval(StrEnum):
    MONTH = "month"
    YEAR = "year"


class PaymentProviderId(StrEnum):
    FAKE = "fake"
    STRIPE = "stripe"
    SBER = "sber"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class PaymentKind(StrEnum):
    CHECKOUT = "checkout"
    RENEWAL = "renewal"
    REFUND = "refund"


class PaymentEventKind(StrEnum):
    CHECKOUT_COMPLETED = "checkout.completed"
    PAYMENT_FAILED = "payment.failed"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    SUBSCRIPTION_CANCELED = "subscription.canceled"


class Entitlement(StrEnum):
    CORE_DIARY = "core_diary"
    REMINDERS = "reminders"
    UNLIMITED_ENTRIES = "unlimited_entries"
    CUSTOM_MOOD_ICONS = "custom_mood_icons"
    EXTRA_ICON_SLOTS = "extra_icon_slots"
    CUSTOM_THEMES = "custom_themes"
    EXTRA_ATTACHMENTS = "extra_attachments"
    ADVANCED_INSIGHTS = "advanced_insights"
    DATA_EXPORT = "data_export"
    COMPANION = "companion"
    UNLIMITED_CUSTOMIZATION = "unlimited_customization"
    PRIORITY_SUPPORT = "priority_support"
    FAMILY_SHARING = "family_sharing"


PLAN_SLUGS = frozenset(slug.value for slug in PlanSlug)
BILLING_INTERVALS = frozenset(item.value for item in BillingInterval)
PAYMENT_PROVIDER_IDS = frozenset(item.value for item in PaymentProviderId)
SUBSCRIPTION_STATUSES = frozenset(item.value for item in SubscriptionStatus)
PAYMENT_STATUSES = frozenset(item.value for item in PaymentStatus)
PAYMENT_KINDS = frozenset(item.value for item in PaymentKind)

ENTITLED_SUBSCRIPTION_STATUSES = frozenset(
    {
        SubscriptionStatus.TRIALING.value,
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.PAST_DUE.value,
    }
)

# Ordered rows for the public comparison table (marketing, not enforcement).
COMPARISON_ENTITLEMENTS: tuple[Entitlement, ...] = (
    Entitlement.CORE_DIARY,
    Entitlement.UNLIMITED_ENTRIES,
    Entitlement.REMINDERS,
    Entitlement.CUSTOM_MOOD_ICONS,
    Entitlement.EXTRA_ICON_SLOTS,
    Entitlement.CUSTOM_THEMES,
    Entitlement.EXTRA_ATTACHMENTS,
    Entitlement.ADVANCED_INSIGHTS,
    Entitlement.DATA_EXPORT,
    Entitlement.COMPANION,
    Entitlement.UNLIMITED_CUSTOMIZATION,
    Entitlement.PRIORITY_SUPPORT,
    Entitlement.FAMILY_SHARING,
)

_FREE_ENTITLEMENTS = frozenset(
    {
        Entitlement.CORE_DIARY.value,
        Entitlement.REMINDERS.value,
        Entitlement.UNLIMITED_ENTRIES.value,
    }
)
_PLUS_ENTITLEMENTS = _FREE_ENTITLEMENTS | {
    Entitlement.CUSTOM_MOOD_ICONS.value,
    Entitlement.EXTRA_ICON_SLOTS.value,
    Entitlement.CUSTOM_THEMES.value,
    Entitlement.EXTRA_ATTACHMENTS.value,
    Entitlement.ADVANCED_INSIGHTS.value,
    Entitlement.DATA_EXPORT.value,
}
_PRO_ENTITLEMENTS = _PLUS_ENTITLEMENTS | {
    Entitlement.COMPANION.value,
    Entitlement.UNLIMITED_CUSTOMIZATION.value,
    Entitlement.PRIORITY_SUPPORT.value,
    Entitlement.FAMILY_SHARING.value,
}


@dataclass(frozen=True, slots=True)
class PlanPrice:
    interval: BillingInterval
    amount_minor: int
    currency: str


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    slug: PlanSlug
    rank: int
    is_default: bool
    is_highlight: bool
    entitlements: frozenset[str]
    prices: tuple[PlanPrice, ...]
    highlight_entitlements: tuple[str, ...]


PLAN_CATALOG: tuple[PlanDefinition, ...] = (
    PlanDefinition(
        slug=PlanSlug.FREE,
        rank=0,
        is_default=True,
        is_highlight=False,
        entitlements=_FREE_ENTITLEMENTS,
        prices=(),
        highlight_entitlements=(
            Entitlement.CORE_DIARY.value,
            Entitlement.UNLIMITED_ENTRIES.value,
            Entitlement.REMINDERS.value,
        ),
    ),
    PlanDefinition(
        slug=PlanSlug.PLUS,
        rank=10,
        is_default=False,
        is_highlight=True,
        entitlements=_PLUS_ENTITLEMENTS,
        prices=(
            PlanPrice(BillingInterval.MONTH, 34900, "RUB"),
            PlanPrice(BillingInterval.YEAR, 299000, "RUB"),
            PlanPrice(BillingInterval.MONTH, 499, "USD"),
            PlanPrice(BillingInterval.YEAR, 4900, "USD"),
        ),
        highlight_entitlements=(
            Entitlement.CUSTOM_MOOD_ICONS.value,
            Entitlement.CUSTOM_THEMES.value,
            Entitlement.ADVANCED_INSIGHTS.value,
            Entitlement.DATA_EXPORT.value,
        ),
    ),
    PlanDefinition(
        slug=PlanSlug.PRO,
        rank=20,
        is_default=False,
        is_highlight=False,
        entitlements=_PRO_ENTITLEMENTS,
        prices=(
            PlanPrice(BillingInterval.MONTH, 69900, "RUB"),
            PlanPrice(BillingInterval.YEAR, 599000, "RUB"),
            PlanPrice(BillingInterval.MONTH, 999, "USD"),
            PlanPrice(BillingInterval.YEAR, 9900, "USD"),
        ),
        highlight_entitlements=(
            Entitlement.UNLIMITED_CUSTOMIZATION.value,
            Entitlement.COMPANION.value,
            Entitlement.FAMILY_SHARING.value,
            Entitlement.PRIORITY_SUPPORT.value,
        ),
    ),
)

PLANS_BY_SLUG: dict[str, PlanDefinition] = {plan.slug.value: plan for plan in PLAN_CATALOG}

DEFAULT_PLAN = next(plan for plan in PLAN_CATALOG if plan.is_default)


def get_plan(slug: str) -> PlanDefinition | None:
    return PLANS_BY_SLUG.get(slug)


def entitlements_for_plan(slug: str) -> frozenset[str]:
    plan = get_plan(slug)
    if plan is None:
        return DEFAULT_PLAN.entitlements
    return plan.entitlements


def prices_for_plan(plan: PlanDefinition, *, currency: str) -> tuple[PlanPrice, ...]:
    wanted = currency.upper()
    return tuple(price for price in plan.prices if price.currency.upper() == wanted)


def plan_price(
    plan: PlanDefinition,
    *,
    interval: BillingInterval | str,
    currency: str,
) -> PlanPrice | None:
    interval_value = interval.value if isinstance(interval, BillingInterval) else interval
    for price in prices_for_plan(plan, currency=currency):
        if price.interval.value == interval_value:
            return price
    return None
