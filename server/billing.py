"""Payments: the only code that talks to Stripe. Switching provider = replacing this file.

Checkout is hosted by Stripe (no card data touches the gateway). Purchases are granted only from signed
webhooks, never from the browser's return to the success page."""

import json
import logging
from dataclasses import dataclass

import stripe

from server.config import Settings

logger = logging.getLogger(__name__)

GRANT_EVENTS = ("checkout.session.completed", "checkout.session.async_payment_succeeded")


@dataclass(frozen=True)
class Product:
    id: str
    label: str
    price_label: str  # display only; Stripe charges what the Price object says
    price_setting: str  # Settings field holding the Stripe Price id
    credits: int = 0
    pass_days: int = 0


PRODUCTS = {
    p.id: p
    for p in (
        Product("credits_5", "5 mock interviews", "$9", "stripe_price_credits_5", credits=5),
        Product("pass_30", "Unlimited mocks for 30 days", "$29", "stripe_price_pass_30", pass_days=30),
    )
}


class BillingError(Exception):
    pass


def _client(settings: Settings) -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise BillingError("payments are not configured on this server")
    return stripe.StripeClient(settings.stripe_secret_key, http_client=stripe.HTTPXClient())


async def create_checkout(settings: Settings, uid: str, product: Product) -> str:
    """A Stripe Checkout page for one product, tied to this user; returns its URL."""
    price = getattr(settings, product.price_setting)
    if not price:
        raise BillingError(f"{product.price_setting.upper()} is not set")
    session = await _client(settings).v1.checkout.sessions.create_async(params={
        "mode": "payment",
        "line_items": [{"price": price, "quantity": 1}],
        "client_reference_id": uid,
        "metadata": {"user_id": uid, "product": product.id},
        "success_url": f"{settings.site_url.rstrip('/')}/new?paid=1",
        "cancel_url": f"{settings.site_url.rstrip('/')}/new",
    })
    return session.url


@dataclass(frozen=True)
class Purchase:
    event_id: str
    session_id: str
    user_id: str
    product: Product
    amount_total: int | None
    currency: str | None


def parse_webhook(settings: Settings, payload: bytes, signature: str) -> Purchase | None:
    """Verify the Stripe signature (raises ValueError if forged, stale or unconfigured) and return the purchase
    to grant, or None for events that grant nothing (other types, not yet paid)."""
    if not settings.stripe_webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not set")
    try:
        stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except stripe.SignatureVerificationError as e:
        raise ValueError("bad signature") from e
    event = json.loads(payload)  # verified: read the raw JSON rather than the SDK's object model
    if event.get("type") not in GRANT_EVENTS:
        return None
    session = event["data"]["object"]
    if session.get("payment_status") != "paid":
        return None  # e.g. bank transfer pending: granted on async_payment_succeeded
    meta = session.get("metadata") or {}
    product = PRODUCTS.get(meta.get("product", ""))
    uid = meta.get("user_id") or session.get("client_reference_id")
    if not product or not uid:
        logger.error("paid checkout %s without a known product/user: %s", session.get("id"), meta)
        return None
    return Purchase(
        event_id=event["id"], session_id=session["id"], user_id=uid, product=product,
        amount_total=session.get("amount_total"), currency=session.get("currency"),
    )
