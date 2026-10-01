"""Billing catalog, fake checkout, cancel, and webhooks."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.core.billing import Entitlement, PlanSlug
from app.core.error_codes import ErrorCode
from app.models.payment import Payment
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.services.billing_service import plan_state_for_user
from app.services.payments.sber import SberPaymentProvider
from app.services.payments.stripe import StripePaymentProvider
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import FakeEmailService, register_verify_and_login


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _billing_on_for_everyone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "feature_billing", True)
    monkeypatch.setattr(settings, "feature_billing_percent", 100)
    monkeypatch.setattr(settings, "feature_billing_emails", "")
    monkeypatch.setattr(settings, "feature_billing_user_ids", "")


def test_plans_catalog(auth_client: TestClient, mailer: FakeEmailService) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-catalog@example.com")
    response = auth_client.get("/v1/billing/plans", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "RUB"
    slugs = [item["slug"] for item in body["items"]]
    assert slugs == ["free", "plus", "pro"]
    plus = next(item for item in body["items"] if item["slug"] == "plus")
    assert plus["is_highlight"] is True
    assert "custom_mood_icons" in plus["entitlements"]
    assert body["current"]["plan_slug"] == "free"
    assert body["current"]["is_paid"] is False
    assert "fake" in body["providers"]


def test_plans_catalog_hidden_from_anonymous(auth_client: TestClient) -> None:
    response = auth_client.get("/v1/billing/plans")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == ErrorCode.BILLING_DISABLED.value


def test_billing_only_for_allowlisted_testers(
    auth_client: TestClient,
    mailer: FakeEmailService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "feature_billing_percent", 0)
    monkeypatch.setattr(settings, "feature_billing_emails", "Tester@Example.com")
    outsider = register_verify_and_login(auth_client, mailer, "plans-outsider@example.com")
    tester = register_verify_and_login(auth_client, mailer, "tester@example.com")

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(outsider)).json()
    assert me["features"]["billing"] is False
    for method, path, body in (
        ("get", "/v1/billing/plans", None),
        ("get", "/v1/billing/subscription", None),
        ("post", "/v1/billing/checkout", {"plan_slug": "plus", "interval": "month"}),
        ("post", "/v1/billing/cancel", None),
    ):
        response = auth_client.request(method, path, headers=_auth_headers(outsider), json=body)
        assert response.status_code == 403, path
        assert response.json()["detail"]["code"] == ErrorCode.BILLING_DISABLED.value

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(tester)).json()
    assert me["features"]["billing"] is True
    plans = auth_client.get("/v1/billing/plans", headers=_auth_headers(tester))
    assert plans.status_code == 200


def test_me_includes_free_plan_by_default(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-free@example.com")
    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    body = me.json()
    assert body["plan"] == "free"
    assert Entitlement.CORE_DIARY.value in body["entitlements"]
    assert Entitlement.CUSTOM_MOOD_ICONS.value not in body["entitlements"]


def test_fake_checkout_activates_plus(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-plus@example.com")
    checkout = auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "plus", "interval": "month"},
    )
    assert checkout.status_code == 200, checkout.text
    payload = checkout.json()
    assert payload["completed"] is True
    assert payload["provider"] == "fake"
    assert payload["plan_slug"] == "plus"
    assert payload["subscription_status"] == "active"

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["plan"] == "plus"
    assert Entitlement.CUSTOM_MOOD_ICONS.value in me.json()["entitlements"]

    catalog = auth_client.get("/v1/billing/plans", headers=_auth_headers(token))
    current = catalog.json()["current"]
    assert current["plan_slug"] == "plus"
    assert current["is_paid"] is True
    assert current["billing_interval"] == "month"

    user = db.scalar(select(User).where(User.email == "plans-plus@example.com"))
    assert user is not None
    payment = db.scalar(select(Payment).where(Payment.user_id == user.id))
    assert payment is not None
    assert payment.status == "succeeded"
    assert payment.amount_minor == 34900


def test_cannot_checkout_free_or_same_plan(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-dup@example.com")
    free = auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "free", "interval": "month"},
    )
    assert free.status_code == 400
    assert free.json()["detail"]["code"] == ErrorCode.PLAN_NOT_PURCHASABLE.value

    paid = auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "plus", "interval": "year"},
    )
    assert paid.status_code == 200
    again = auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "plus", "interval": "year"},
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == ErrorCode.ALREADY_ON_PLAN.value


def test_upgrade_plus_to_pro(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-pro@example.com")
    auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "plus", "interval": "month"},
    )
    pro = auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "pro", "interval": "year"},
    )
    assert pro.status_code == 200
    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["plan"] == "pro"
    assert Entitlement.COMPANION.value in me.json()["entitlements"]


def test_cancel_keeps_access_until_period_end(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-cancel@example.com")
    auth_client.post(
        "/v1/billing/checkout",
        headers=_auth_headers(token),
        json={"plan_slug": "plus", "interval": "month"},
    )
    canceled = auth_client.post("/v1/billing/cancel", headers=_auth_headers(token))
    assert canceled.status_code == 200
    body = canceled.json()
    assert body["cancel_at_period_end"] is True
    assert body["plan_slug"] == "plus"
    assert body["is_paid"] is True

    me = auth_client.get("/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["plan"] == "plus"

    user = db.scalar(select(User).where(User.email == "plans-cancel@example.com"))
    assert user is not None
    assert user.subscription is not None
    user.subscription.current_period_end = datetime.now(UTC) - timedelta(hours=1)
    db.flush()
    db.expire(user, ["subscription"])
    assert plan_state_for_user(user).slug == PlanSlug.FREE.value


def test_cancel_without_subscription(
    auth_client: TestClient,
    mailer: FakeEmailService,
) -> None:
    token = register_verify_and_login(auth_client, mailer, "plans-none@example.com")
    response = auth_client.post("/v1/billing/cancel", headers=_auth_headers(token))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == ErrorCode.NO_ACTIVE_SUBSCRIPTION.value


def test_fake_webhook_completes_pending_checkout(
    auth_client: TestClient,
    mailer: FakeEmailService,
    db: Session,
) -> None:
    register_verify_and_login(auth_client, mailer, "plans-hook@example.com")
    user = db.scalar(select(User).where(User.email == "plans-hook@example.com"))
    assert user is not None
    payment = Payment(
        user_id=user.id,
        plan_slug="plus",
        billing_interval="month",
        provider="fake",
        provider_session_id=f"fake_cs_{uuid.uuid4().hex}",
        kind="checkout",
        status="pending",
        amount_minor=34900,
        currency="RUB",
        extra={},
    )
    db.add(payment)
    db.flush()

    first = auth_client.post(
        "/v1/billing/webhooks/fake",
        content=json.dumps(
            {
                "id": "evt_test_1",
                "type": "checkout.completed",
                "session_id": payment.provider_session_id,
                "subscription_id": "fake_sub_webhook",
                "metadata": {"payment_id": str(payment.id)},
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    assert first.status_code == 200
    assert first.json()["applied"] == 1

    second = auth_client.post(
        "/v1/billing/webhooks/fake",
        content=json.dumps(
            {
                "id": "evt_test_1",
                "type": "checkout.completed",
                "session_id": payment.provider_session_id,
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    assert second.status_code == 200
    assert second.json()["applied"] == 0

    db.expire_all()
    row = db.get(Payment, payment.id)
    assert row is not None
    assert row.status == "succeeded"
    sub = db.scalar(select(UserSubscription).where(UserSubscription.user_id == user.id))
    assert sub is not None
    assert sub.plan_slug == "plus"


def test_stripe_and_sber_are_scaffolds() -> None:
    stripe = StripePaymentProvider()
    assert stripe.is_configured() is False
    sber = SberPaymentProvider()
    assert sber.is_configured() is False
    payload = stripe.checkout_payload
    assert callable(payload)
    from app.core.billing import BillingInterval
    from app.services.payments.base import CheckoutRequest

    request = CheckoutRequest(
        user_id=uuid.uuid4(),
        customer_email="a@b.c",
        plan_slug="plus",
        interval=BillingInterval.MONTH,
        amount_minor=499,
        currency="USD",
        success_url="https://example.com/ok",
        cancel_url="https://example.com/no",
        idempotency_key="key",
    )
    assert stripe.checkout_payload(request)["mode"] == "subscription"
    assert sber.register_order_payload(request)["amount"] == 499
