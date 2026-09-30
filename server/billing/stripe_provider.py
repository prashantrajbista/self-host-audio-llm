"""Stripe Checkout (hosted page; no card data touches the gateway). Kept for when Stripe serves Nepal."""

import json
import logging
from collections.abc import Mapping

import stripe

from server.billing import PRODUCTS, BillingError, Product, Purchase
from server.config import Settings

logger = logging.getLogger(__name__)

GRANT_EVENTS = ("checkout.session.completed", "checkout.session.async_payment_succeeded")


def _client(settings: Settings) -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise BillingError("payments are not configured on this server")
    return stripe.StripeClient(settings.stripe_secret_key, http_client=stripe.HTTPXClient())


async def create_checkout(settings: Settings, uid: str, product: Product) -> dict:
    """A Stripe Checkout page for one product, tied to this user."""
    price = getattr(settings, product.stripe_price_setting)
    if not price:
        raise BillingError(f"{product.stripe_price_setting.upper()} is not set")
    session = await _client(settings).v1.checkout.sessions.create_async(params={
        "mode": "payment",
        "line_items": [{"price": price, "quantity": 1}],
        "client_reference_id": uid,
        "metadata": {"user_id": uid, "product": product.id},
        "success_url": f"{settings.site_url.rstrip('/')}/new?paid=1",
        "cancel_url": f"{settings.site_url.rstrip('/')}/new",
    })
    return {"provider": "stripe", "url": session.url}


def parse_webhook(settings: Settings, payload: bytes, headers: Mapping[str, str]) -> Purchase | None:
    """Verify the Stripe signature (raises ValueError if forged, stale or unconfigured) and return the purchase
    to grant, or None for events that grant nothing (other types, not yet paid)."""
    if not settings.stripe_webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not set")
    try:
        stripe.Webhook.construct_event(payload, headers.get("stripe-signature", ""), settings.stripe_webhook_secret)
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
        provider="stripe", event_id=event["id"], session_id=session["id"], user_id=uid, product=product,
        amount_total=session.get("amount_total"), currency=session.get("currency"),
    )
