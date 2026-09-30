"""Payments. The provider modules are the only code that talks to a payment company; PAYMENT_PROVIDER picks one.

Purchases are granted only from signed webhooks, never from the browser coming back from checkout.
Adding a provider = a module with create_checkout(settings, uid, product) -> dict and
parse_webhook(settings, payload, headers) -> Purchase | None, plus a branch in _provider."""

from collections.abc import Mapping
from dataclasses import dataclass

from server.config import Settings


@dataclass(frozen=True)
class Product:
    id: str
    label: str
    price_label: str  # display only; the provider charges what its price object says
    stripe_price_setting: str  # Settings fields holding each provider's price id
    paddle_price_setting: str
    credits: int = 0
    pass_days: int = 0


PRODUCTS = {
    p.id: p
    for p in (
        Product("credits_5", "5 mock interviews", "$9", "stripe_price_credits_5", "paddle_price_credits_5", credits=5),
        Product("pass_30", "Unlimited mocks for 30 days", "$29", "stripe_price_pass_30", "paddle_price_pass_30", pass_days=30),
    )
}


@dataclass(frozen=True)
class Purchase:
    provider: str
    event_id: str
    session_id: str  # the provider's checkout/transaction id: one grant per checkout
    user_id: str
    product: Product
    amount_total: int | None
    currency: str | None


class BillingError(Exception):
    pass


def _provider(settings: Settings):
    if settings.payment_provider == "paddle":
        from server.billing import paddle_provider

        return paddle_provider
    if settings.payment_provider == "stripe":
        from server.billing import stripe_provider

        return stripe_provider
    raise BillingError(f"unknown PAYMENT_PROVIDER {settings.payment_provider!r}")


async def create_checkout(settings: Settings, uid: str, product: Product) -> dict:
    """What the browser needs to open checkout: {"provider", "url"} (Stripe) or {"provider", "transaction_id"} (Paddle)."""
    return await _provider(settings).create_checkout(settings, uid, product)


def parse_webhook(settings: Settings, payload: bytes, headers: Mapping[str, str]) -> Purchase | None:
    """Verify and read a provider webhook. Raises ValueError if it isn't genuine; None = nothing to grant."""
    return _provider(settings).parse_webhook(settings, payload, headers)
