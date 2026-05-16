"""Razorpay Subscriptions API wrapper.

Thin layer over the official `razorpay` Python SDK so the rest of the
application doesn't need to know about Razorpay's request shape.

The pieces we use:
  - `client.subscription.create(...)`  — start a recurring subscription
  - `client.subscription.cancel(sub_id, {"cancel_at_cycle_end": 1})`
  - `client.utility.verify_webhook_signature(body, sig, secret)`

Webhook events we react to (handler lives in `endpoints/billing.py`):
  - subscription.activated   → tier=plus,   status=active
  - subscription.charged     → extend period_end
  - subscription.halted      → status=past_due (Razorpay couldn't charge)
  - subscription.cancelled   → status=canceled (stays Plus until period_end,
                               then we downgrade on access)
  - subscription.completed   → status=expired, tier=free
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.config import settings

log = logging.getLogger(__name__)


def _client():
    """Lazy-construct the Razorpay client so missing env doesn't crash boot."""
    import razorpay  # local import — keeps boot light if billing is unused

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError(
            "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not configured. "
            "Set them in your .env to enable subscriptions."
        )
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_monthly_subscription(
    *,
    user_email: str,
    user_name: Optional[str],
    total_count: int = 120,  # 10 years; renews monthly until canceled
    notes: Optional[dict[str, str]] = None,
    offer_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a Razorpay subscription on the monthly Plus plan.

    `offer_id` (optional) attaches a pre-configured Razorpay Offer so the first
    cycle is billed at a discounted price (e.g. EARLYSALE → ₹49 first month).
    Subsequent cycles charge the base plan amount automatically.

    Returns the raw Razorpay subscription object — callers persist the `id`
    on the user as `subscription_external_id` and pass `id` to the
    Razorpay Checkout JS on the client.
    """
    if not settings.RAZORPAY_PLAN_ID_MONTHLY:
        raise RuntimeError(
            "RAZORPAY_PLAN_ID_MONTHLY not configured. Create a recurring "
            "monthly plan in the Razorpay dashboard and set its id."
        )
    payload: dict[str, Any] = {
        "plan_id": settings.RAZORPAY_PLAN_ID_MONTHLY,
        "total_count": total_count,
        "customer_notify": 1,
        "notes": {
            "email": user_email,
            "name": user_name or "",
            **(notes or {}),
        },
    }
    if offer_id:
        payload["offer_id"] = offer_id
    log.info("razorpay.subscription.create payload=%s", payload)
    return _client().subscription.create(payload)


def create_one_time_order(
    *,
    amount_paise: int,
    notes: Optional[dict[str, str]] = None,
    receipt: Optional[str] = None,
) -> dict[str, Any]:
    """Create a Razorpay Order for a one-time ₹200 Plus purchase.

    Returns the raw Razorpay order — callers pass `id` + `amount` to
    Razorpay Checkout JS in "Order" mode (no subscription / e-mandate).
    """
    payload: dict[str, Any] = {
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": notes or {},
    }
    if receipt:
        payload["receipt"] = receipt
    log.info("razorpay.order.create payload=%s", payload)
    return _client().order.create(payload)


def verify_order_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify the HMAC signature returned by Razorpay Checkout for an Order.

    Razorpay returns (razorpay_order_id, razorpay_payment_id, razorpay_signature)
    on successful payment; signature is HMAC-SHA256(order_id|payment_id, key_secret).
    """
    try:
        _client().utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
        return True
    except Exception as exc:
        log.warning("razorpay order signature verification failed: %s", exc)
        return False


def fetch_payment(payment_id: str) -> dict[str, Any]:
    return _client().payment.fetch(payment_id)


def cancel_subscription(subscription_id: str, *, at_cycle_end: bool = True) -> dict[str, Any]:
    """Cancel a Razorpay subscription. Defaults to end-of-cycle cancel."""
    options = {"cancel_at_cycle_end": 1 if at_cycle_end else 0}
    return _client().subscription.cancel(subscription_id, options)


def fetch_subscription(subscription_id: str) -> dict[str, Any]:
    return _client().subscription.fetch(subscription_id)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify the X-Razorpay-Signature header against the raw request body.

    Raises a SignatureVerificationError from the SDK if invalid; we wrap that
    into a simple boolean for the endpoint to act on.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise RuntimeError("RAZORPAY_WEBHOOK_SECRET not configured.")
    try:
        _client().utility.verify_webhook_signature(
            body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
        return True
    except Exception as exc:
        log.warning("razorpay webhook signature verification failed: %s", exc)
        return False
