"""Paddle Billing (merchant of record). The server creates the transaction, so the price and the buyer's user
id are set here, not in the browser; the browser only opens Paddle's overlay for that transaction id."""

import hashlib
import hmac
import json
import logging
import time
from collections.abc import Mapping

from server.adapters.http_client import shared_client
from server.billing import PRODUCTS, BillingError, Product, Purchase
from server.config import Settings

logger = logging.getLogger(__name__)

API_BASE = {"sandbox": "https://sandbox-api.paddle.com", "production": "https://api.paddle.com"}
SIGNATURE_TOLERANCE_S = 300  # reject replayed webhooks older than this


async def create_checkout(settings: Settings, uid: str, product: Product) -> dict:
    price = getattr(settings, product.paddle_price_setting)
    base = API_BASE.get(settings.paddle_env)
    if not settings.paddle_api_key or not price or not base:
        raise BillingError("Paddle is not configured (PADDLE_API_KEY, PADDLE_ENV, price ids)")
    r = await shared_client().post(
        f"{base}/transactions",
        json={"items": [{"price_id": price, "quantity": 1}], "custom_data": {"user_id": uid, "product": product.id}},
        headers={"Authorization": f"Bearer {settings.paddle_api_key}"},
    )
    if r.status_code >= 400:
        raise BillingError(f"Paddle HTTP {r.status_code}: {r.text[:300]}")
    return {"provider": "paddle", "transaction_id": r.json()["data"]["id"]}


def _verify(secret: str, payload: bytes, header: str) -> None:
    """Paddle-Signature: "ts=<unix>;h1=<hex>" (several h1 while a secret is being rotated).
    h1 = HMAC-SHA256(secret, "<ts>:<raw body>")."""
    parts = [p.split("=", 1) for p in header.split(";") if "=" in p]
    ts = next((v for k, v in parts if k == "ts"), "")
    signatures = [v for k, v in parts if k == "h1"]
    if not ts.isdigit() or not signatures or abs(time.time() - int(ts)) > SIGNATURE_TOLERANCE_S:
        raise ValueError("missing or stale signature")
    expected = hmac.new(secret.encode(), ts.encode() + b":" + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise ValueError("bad signature")


def parse_webhook(settings: Settings, payload: bytes, headers: Mapping[str, str]) -> Purchase | None:
    if not settings.paddle_webhook_secret:
        raise ValueError("PADDLE_WEBHOOK_SECRET is not set")
    _verify(settings.paddle_webhook_secret, payload, headers.get("paddle-signature", ""))
    event = json.loads(payload)
    if event.get("event_type") != "transaction.completed":
        return None
    txn = event["data"]
    meta = txn.get("custom_data") or {}
    product = PRODUCTS.get(meta.get("product", ""))
    uid = meta.get("user_id")
    charged = {i.get("price_id") or (i.get("price") or {}).get("id") for i in txn.get("items") or []}
    # custom_data comes from our own create_checkout; also require it matches what was actually charged
    if not product or not uid or getattr(settings, product.paddle_price_setting) not in charged:
        logger.error("completed Paddle transaction %s doesn't match a product/user: %s %s", txn.get("id"), meta, charged)
        return None
    total = ((txn.get("details") or {}).get("totals") or {}).get("grand_total")
    return Purchase(
        provider="paddle", event_id=event["event_id"], session_id=txn["id"], user_id=uid, product=product,
        amount_total=int(total) if str(total or "").isdigit() else None, currency=txn.get("currency_code"),
    )
