"""In-process payment provider for local development and tests."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.core.billing import PaymentEventKind, PaymentProviderId
from app.core.error_codes import ErrorCode
from app.services.payments.base import (
    BasePaymentProvider,
    CheckoutRequest,
    CheckoutSession,
    PaymentError,
    PaymentEvent,
)


class FakePaymentProvider(BasePaymentProvider):
    """Settles checkout in the same request. No external HTTP.

    Webhooks accept unsigned JSON so tests can exercise the async path:

    ``{"id": "evt_…", "type": "checkout.completed", "session_id": "fake_cs_…"}``
    """

    def __init__(self, *, instant_complete: bool = True) -> None:
        self._instant_complete = instant_complete
        self.canceled_subscription_ids: list[str] = []

    @property
    def provider_id(self) -> PaymentProviderId:
        return PaymentProviderId.FAKE

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        session_id = f"fake_cs_{uuid.uuid4().hex}"
        subscription_id = f"fake_sub_{uuid.uuid4().hex}"
        payment_id = f"fake_pay_{uuid.uuid4().hex}"
        return CheckoutSession(
            provider=PaymentProviderId.FAKE,
            provider_session_id=session_id,
            provider_subscription_id=subscription_id,
            provider_payment_id=payment_id,
            instant_complete=self._instant_complete,
            checkout_url=None if self._instant_complete else request.success_url,
        )

    def parse_webhook(
        self,
        *,
        headers: Mapping[str, str],
        body: bytes,
    ) -> Sequence[PaymentEvent]:
        del headers
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentError(
                "Invalid fake webhook payload",
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                status_code=400,
            ) from exc
        if not isinstance(payload, dict):
            raise PaymentError(
                "Invalid fake webhook payload",
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                status_code=400,
            )
        event_id = str(payload.get("id") or "").strip()
        event_type = str(payload.get("type") or "").strip()
        if not event_id or not event_type:
            raise PaymentError(
                "Fake webhook requires id and type",
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                status_code=400,
            )
        kind_map = {
            "checkout.completed": PaymentEventKind.CHECKOUT_COMPLETED,
            "payment.failed": PaymentEventKind.PAYMENT_FAILED,
            "subscription.renewed": PaymentEventKind.SUBSCRIPTION_RENEWED,
            "subscription.canceled": PaymentEventKind.SUBSCRIPTION_CANCELED,
        }
        kind = kind_map.get(event_type)
        if kind is None:
            raise PaymentError(
                f"Unknown fake webhook type: {event_type}",
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                status_code=400,
                params={"event_type": event_type},
            )
        raw_metadata = payload.get("metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        return [
            PaymentEvent(
                provider=PaymentProviderId.FAKE,
                provider_event_id=event_id,
                kind=kind,
                provider_session_id=_optional_str(payload.get("session_id")),
                provider_payment_id=_optional_str(payload.get("payment_id")),
                provider_subscription_id=_optional_str(payload.get("subscription_id")),
                amount_minor=_optional_int(payload.get("amount_minor")),
                currency=_optional_str(payload.get("currency")),
                paid_at=datetime.now(UTC) if kind is PaymentEventKind.CHECKOUT_COMPLETED else None,
                metadata={str(key): str(value) for key, value in metadata.items()},
                raw=payload,
            )
        ]

    def cancel_subscription(
        self,
        *,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> None:
        del at_period_end
        self.canceled_subscription_ids.append(provider_subscription_id)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
