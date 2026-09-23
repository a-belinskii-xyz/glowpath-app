from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.config import settings
from app.core.billing import PaymentProviderId
from app.core.error_codes import ErrorCode
from app.core.feature_flags import parse_csv
from app.services.payments.base import BasePaymentProvider, PaymentError
from app.services.payments.fake import FakePaymentProvider
from app.services.payments.sber import SberPaymentProvider
from app.services.payments.stripe import StripePaymentProvider


class PaymentProviderRegistry:
    """Looks up enabled payment processors by id."""

    def __init__(
        self,
        providers: Mapping[PaymentProviderId, BasePaymentProvider],
        *,
        enabled_ids: Iterable[str],
        default_id: str,
    ) -> None:
        self._providers = dict(providers)
        enabled: list[PaymentProviderId] = []
        for raw in enabled_ids:
            try:
                provider_id = PaymentProviderId(raw.strip().lower())
            except ValueError:
                continue
            provider = self._providers.get(provider_id)
            if provider is None:
                continue
            enabled.append(provider_id)
        if not enabled:
            enabled = [PaymentProviderId.FAKE]
        self._enabled = tuple(dict.fromkeys(enabled))
        try:
            default = PaymentProviderId(default_id.strip().lower())
        except ValueError:
            default = self._enabled[0]
        if default not in self._enabled:
            default = self._enabled[0]
        self._default = default

    @property
    def default_id(self) -> PaymentProviderId:
        return self._default

    @property
    def enabled_ids(self) -> tuple[PaymentProviderId, ...]:
        return self._enabled

    def get(self, provider_id: PaymentProviderId | str | None) -> BasePaymentProvider:
        if provider_id is None or str(provider_id).strip() == "":
            chosen = self._default
        else:
            raw = provider_id.value if isinstance(provider_id, PaymentProviderId) else provider_id
            try:
                chosen = PaymentProviderId(raw.strip().lower())
            except ValueError as exc:
                raise PaymentError(
                    f"Unknown payment provider: {raw}",
                    code=ErrorCode.PAYMENT_PROVIDER_UNKNOWN,
                    status_code=400,
                    params={"provider": str(raw)},
                ) from exc
        if chosen not in self._enabled:
            raise PaymentError(
                f"Payment provider is not enabled: {chosen}",
                code=ErrorCode.PAYMENT_PROVIDER_DISABLED,
                status_code=400,
                params={"provider": chosen.value},
            )
        provider = self._providers[chosen]
        if not provider.is_configured():
            raise PaymentError(
                f"Payment provider is not configured: {chosen}",
                code=ErrorCode.PAYMENT_PROVIDER_NOT_CONFIGURED,
                status_code=501,
                params={"provider": chosen.value},
            )
        return provider

    def public_providers(self) -> list[PaymentProviderId]:
        return [
            provider_id
            for provider_id in self._enabled
            if self._providers[provider_id].is_configured()
        ]


def build_payment_registry(
    *,
    fake: FakePaymentProvider | None = None,
) -> PaymentProviderRegistry:
    providers: dict[PaymentProviderId, BasePaymentProvider] = {
        PaymentProviderId.FAKE: fake if fake is not None else FakePaymentProvider(),
        PaymentProviderId.STRIPE: StripePaymentProvider(
            secret_key=settings.stripe_secret_key,
            webhook_secret=settings.stripe_webhook_secret,
        ),
        PaymentProviderId.SBER: SberPaymentProvider(
            username=settings.sber_username,
            password=settings.sber_password,
        ),
    }
    enabled_raw = parse_csv(settings.billing_enabled_providers)
    enabled = enabled_raw if enabled_raw else (PaymentProviderId.FAKE.value,)
    return PaymentProviderRegistry(
        providers,
        enabled_ids=enabled,
        default_id=settings.billing_default_provider,
    )


payment_registry = build_payment_registry()
