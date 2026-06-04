"""Roammate Plus billing endpoints.

Exposes:
  - GET  /billing/status                         — read entitlement
  - POST /billing/razorpay/subscription          — create Razorpay sub
  - POST /billing/razorpay/webhook               — Razorpay event ingest
  - POST /billing/cancel                         — cancel active subscription

The Apple IAP verify + Server-to-Server-Notification handlers land alongside
these in step 3 of the rollout.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.all_models import SubscriptionEvent, User
from app.services import coupons as coupons_service
from app.services import entitlements
from app.services.payments import app_store_server, apple_service, razorpay_service

log = logging.getLogger(__name__)

router = APIRouter()


# ── 1. Read entitlement ─────────────────────────────────────────────────────

@router.get("/status")
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the caller's current entitlement DTO.

    Clients call this on app boot and after a successful subscription
    transaction to refresh their local view of the user's tier/quotas.
    """
    ent = await entitlements.get_entitlement(db, current_user)
    return ent.to_dto()


# ── 2. Razorpay: create subscription ────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    coupon_code: Optional[str] = None


@router.post("/razorpay/subscription")
async def create_razorpay_subscription(
    body: CreateSubscriptionRequest = CreateSubscriptionRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Razorpay subscription for the caller and return the id.

    The client passes the returned `subscription_id` and `key_id` to
    Razorpay Checkout (`razorpay({ subscription_id, key, ... })`). After the
    user authorizes the e-mandate / pays, Razorpay fires
    `subscription.activated` to our webhook which is when we flip the user
    to Plus. Until then the user remains on free.

    If `coupon_code` is provided, we validate it as a `subscription` target
    and attach the coupon's `razorpay_offer_id` so the first cycle is billed
    at the offer price. Redemption is recorded when the first charge webhook
    arrives (see /razorpay/webhook).
    """
    coupon_quote = None
    if body.coupon_code:
        coupon_quote = await coupons_service.validate_and_quote(
            db, current_user, body.coupon_code, target="subscription"
        )

    notes: dict[str, str] = {"user_id": str(current_user.id)}
    offer_id: Optional[str] = None
    if coupon_quote:
        notes["coupon_id"] = str(coupon_quote.coupon_id)
        offer_id = coupon_quote.razorpay_offer_id

    try:
        sub = razorpay_service.create_monthly_subscription(
            user_email=current_user.email,
            user_name=current_user.name,
            notes=notes,
            offer_id=offer_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.exception("razorpay create subscription failed")
        raise HTTPException(status_code=502, detail="Could not start subscription") from exc

    # Stash the external id so the webhook handler can correlate. We don't
    # flip the tier yet — the webhook is the source of truth.
    current_user.subscription_provider = "razorpay"
    current_user.subscription_external_id = sub["id"]
    if current_user.subscription_status in (None, "none", "expired", "canceled"):
        current_user.subscription_status = "pending"
    await db.commit()

    return {
        "subscription_id": sub["id"],
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "plan_id": settings.RAZORPAY_PLAN_ID_MONTHLY,
        "amount_inr": settings.PLUS_MONTHLY_PRICE_INR,
        "coupon": coupon_quote.to_dto() if coupon_quote else None,
        "user": {"email": current_user.email, "name": current_user.name},
    }


# ── 2b. Coupon validation (preview only — does NOT redeem) ─────────────────

class ValidateCouponRequest(BaseModel):
    code: str
    target: Literal["one_time", "subscription"]


@router.post("/coupons/validate")
async def validate_coupon(
    body: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a CouponQuote for the given code + target without reserving it.

    Used by the paywall UI to preview the final charge before checkout.
    Redemption only happens at successful payment / grant time.
    """
    quote = await coupons_service.validate_and_quote(
        db, current_user, body.code, target=body.target
    )
    return quote.to_dto()


# ── 2c. One-time purchase (₹200 / 30 days, hard-expires to free) ───────────

class OneTimeCreateRequest(BaseModel):
    coupon_code: Optional[str] = None


@router.post("/razorpay/one-time")
async def create_one_time_purchase(
    body: OneTimeCreateRequest = OneTimeCreateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start the one-time Plus purchase.

    If a coupon brings the final price to ₹0, we bypass Razorpay entirely
    and grant Plus directly with a CouponRedemption(provider=internal_grant)
    row in the same transaction. Otherwise we create a Razorpay Order and
    return its id for Checkout.
    """
    coupon_quote = None
    if body.coupon_code:
        coupon_quote = await coupons_service.validate_and_quote(
            db, current_user, body.coupon_code, target="one_time"
        )

    final_paise = (
        coupon_quote.final_amount_paise
        if coupon_quote
        else settings.PLUS_ONETIME_PRICE_INR * 100
    )

    # Free grant path — coupon zeroes the price
    if final_paise == 0:
        assert coupon_quote is not None
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=settings.PLUS_ONETIME_DURATION_DAYS)
        current_user.subscription_tier = "plus"
        current_user.subscription_status = "one_time"
        current_user.subscription_provider = "internal_grant"
        current_user.subscription_current_period_end = period_end
        current_user.last_one_time_purchase_at = now
        current_user.last_one_time_external_id = f"grant_{uuid.uuid4().hex}"
        await coupons_service.record_redemption(
            db,
            current_user,
            coupon_id=coupon_quote.coupon_id,
            provider="internal_grant",
            payment_external_id=current_user.last_one_time_external_id,
            amount_paid_paise=0,
        )
        await db.commit()
        ent = await entitlements.get_entitlement(db, current_user)
        return {
            "granted": True,
            "period_end": period_end.isoformat(),
            "entitlement": ent.to_dto(),
        }

    # Paid path — create Razorpay Order
    notes: dict[str, str] = {
        "user_id": str(current_user.id),
        "type": "one_time",
    }
    if coupon_quote:
        notes["coupon_id"] = str(coupon_quote.coupon_id)
    try:
        order = razorpay_service.create_one_time_order(
            amount_paise=final_paise,
            notes=notes,
            receipt=f"otp_{current_user.id}_{int(time.time())}",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.exception("razorpay create order failed")
        raise HTTPException(status_code=502, detail="Could not start purchase") from exc

    return {
        "granted": False,
        "order_id": order["id"],
        "amount_paise": final_paise,
        "currency": "INR",
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "coupon": coupon_quote.to_dto() if coupon_quote else None,
        "user": {"email": current_user.email, "name": current_user.name},
    }


class OneTimeVerifyRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str
    coupon_id: Optional[int] = None


@router.post("/razorpay/one-time/verify")
async def verify_one_time_purchase(
    body: OneTimeVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify Razorpay Checkout signature, capture state, flip user to one_time Plus."""
    if not razorpay_service.verify_order_signature(body.order_id, body.payment_id, body.signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    try:
        payment = razorpay_service.fetch_payment(body.payment_id)
    except Exception as exc:
        log.exception("razorpay fetch_payment failed")
        raise HTTPException(status_code=502, detail="Could not verify payment") from exc

    if payment.get("status") not in {"captured", "authorized"}:
        raise HTTPException(status_code=400, detail=f"Payment not captured (status={payment.get('status')})")

    # Idempotency: replay the same payment_id → no double grant
    event_insert = (
        pg_insert(SubscriptionEvent)
        .values(
            user_id=current_user.id,
            provider="razorpay",
            event_id=f"one_time:{body.payment_id}",
            event_type="one_time.captured",
            raw_payload={"order_id": body.order_id, "payment": payment},
        )
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(SubscriptionEvent.id)
    )
    inserted = (await db.execute(event_insert)).first()

    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=settings.PLUS_ONETIME_DURATION_DAYS)
    current_user.subscription_tier = "plus"
    current_user.subscription_status = "one_time"
    current_user.subscription_provider = "razorpay"
    current_user.subscription_current_period_end = period_end
    current_user.last_one_time_purchase_at = now
    current_user.last_one_time_external_id = body.payment_id

    if inserted is not None and body.coupon_id:
        await coupons_service.record_redemption(
            db,
            current_user,
            coupon_id=body.coupon_id,
            provider="razorpay",
            payment_external_id=body.payment_id,
            amount_paid_paise=int(payment.get("amount", 0)),
        )

    await db.commit()
    ent = await entitlements.get_entitlement(db, current_user)
    return {"ok": True, "entitlement": ent.to_dto()}


# ── 3. Razorpay: webhook ────────────────────────────────────────────────────

_PLUS_ACTIVATING_EVENTS = {"subscription.activated", "subscription.charged", "subscription.resumed"}
_DEGRADE_EVENTS = {"subscription.halted"}
_TERMINAL_EVENTS = {"subscription.cancelled", "subscription.completed", "subscription.expired"}


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Receive Razorpay events, verify signature, mutate user state.

    Idempotent: every event is stamped by `(provider, event_id)` in
    `subscription_event`. Replays no-op.
    """
    body = await request.body()
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    try:
        ok = razorpay_service.verify_webhook_signature(body, x_razorpay_signature)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body.decode("utf-8"))
    event_id = payload.get("id") or payload.get("event_id") or ""
    event_type = payload.get("event") or "unknown"

    sub_entity = (
        payload.get("payload", {})
        .get("subscription", {})
        .get("entity", {})
    )
    subscription_id = sub_entity.get("id")
    if not subscription_id:
        log.info("razorpay webhook %s ignored (no subscription id)", event_type)
        return {"ok": True, "ignored": True}

    # Find the user this subscription belongs to.
    stmt = select(User).where(User.subscription_external_id == subscription_id)
    user = (await db.execute(stmt)).scalars().first()
    if user is None:
        # Fallback: notes.user_id was set when we created the sub.
        notes = sub_entity.get("notes") or {}
        uid = notes.get("user_id")
        if uid:
            user = (await db.execute(select(User).where(User.id == int(uid)))).scalars().first()
    if user is None:
        log.warning("razorpay webhook %s: no user for subscription %s", event_type, subscription_id)
        return {"ok": True, "ignored": True}

    # Idempotency: insert event row first; if conflict, this is a replay.
    insert_stmt = (
        pg_insert(SubscriptionEvent)
        .values(
            user_id=user.id,
            provider="razorpay",
            event_id=event_id or f"{event_type}:{subscription_id}:{sub_entity.get('current_end','')}",
            event_type=event_type,
            raw_payload=payload,
        )
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(SubscriptionEvent.id)
    )
    new_event = (await db.execute(insert_stmt)).first()
    if new_event is None:
        log.info("razorpay webhook %s replay ignored", event_id)
        return {"ok": True, "replay": True}

    current_end_ts = sub_entity.get("current_end")
    if current_end_ts:
        user.subscription_current_period_end = datetime.fromtimestamp(
            current_end_ts, tz=timezone.utc
        )

    if event_type in _PLUS_ACTIVATING_EVENTS:
        user.subscription_tier = "plus"
        user.subscription_status = "active"
        user.subscription_provider = "razorpay"
        user.subscription_external_id = subscription_id
        # First-cycle coupon redemption (idempotent via unique constraint)
        notes = sub_entity.get("notes") or {}
        coupon_id_raw = notes.get("coupon_id")
        if coupon_id_raw:
            try:
                payment_entity = (
                    payload.get("payload", {}).get("payment", {}).get("entity", {})
                )
                await coupons_service.record_redemption(
                    db,
                    user,
                    coupon_id=int(coupon_id_raw),
                    provider="razorpay",
                    payment_external_id=payment_entity.get("id") or subscription_id,
                    amount_paid_paise=int(payment_entity.get("amount") or 0),
                )
            except Exception:
                log.exception("Failed to record coupon redemption (non-fatal)")
    elif event_type in _DEGRADE_EVENTS:
        user.subscription_status = "past_due"
    elif event_type in _TERMINAL_EVENTS:
        # Cancel-at-cycle-end: keep Plus until period_end; entitlement service
        # will see status=canceled + period_end in the past and treat as free.
        # For `completed` and `expired` we hard-downgrade now.
        if event_type == "subscription.cancelled":
            user.subscription_status = "canceled"
        else:
            user.subscription_tier = "free"
            user.subscription_status = "expired"

    await db.commit()
    log.info("razorpay webhook %s applied for user=%s", event_type, user.id)
    return {"ok": True}


# ── 4. Apple IAP: verify a StoreKit 2 transaction ──────────────────────────

class AppleVerifyRequest(BaseModel):
    signed_transaction_info: str
    coupon_id: Optional[int] = None


@router.post("/apple/verify")
async def verify_apple_transaction(
    body: AppleVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a JWS `signedTransactionInfo` blob from StoreKit 2 and flip the
    caller to Plus. The client calls this immediately after a successful
    purchase or restore; ground-truth state updates flow in later via
    `/billing/apple/webhook` (App Store Server Notifications V2).

    Supports both the monthly auto-renewable subscription and the one-time
    non-renewing subscription (₹200 / 30 days). For non-renewing subs Apple's
    JWS has no `expiresDate`, so we compute period_end = now + 30 days.
    """
    try:
        tx = apple_service.decode_signed_transaction(body.signed_transaction_info)
    except apple_service.VerificationException as exc:
        log.warning("Apple JWS signature verification failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_signature", "message": "Transaction signature invalid."},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not tx.is_valid_product:
        raise HTTPException(
            status_code=400,
            detail=f"Unexpected product/bundle: {tx.bundle_id}/{tx.product_id}",
        )

    current_user.subscription_environment = tx.environment

    is_one_time = tx.is_one_time

    # Audit log + idempotency. For one-time grants we also use this as
    # the redemption gate: only credit a coupon on the first insert.
    insert_stmt = (
        pg_insert(SubscriptionEvent)
        .values(
            user_id=current_user.id,
            provider="apple",
            event_id=tx.transaction_id,
            event_type="apple.one_time.verify" if is_one_time else "apple.verify",
            raw_payload={
                "transaction_id": tx.transaction_id,
                "original_transaction_id": tx.original_transaction_id,
                "product_id": tx.product_id,
                "environment": tx.environment,
                "expires_date": tx.expires_date.isoformat() if tx.expires_date else None,
            },
        )
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(SubscriptionEvent.id)
    )
    inserted = (await db.execute(insert_stmt)).first()

    # Flip user state. If another Apple ID was previously linked we overwrite —
    # the most recent verified transaction wins. (Cross-account fraud is
    # mitigated because Apple binds the transaction to a single Apple ID.)
    current_user.subscription_provider = "apple"
    current_user.subscription_external_id = tx.original_transaction_id

    if is_one_time:
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=settings.PLUS_ONETIME_DURATION_DAYS)
        current_user.subscription_current_period_end = period_end
        current_user.subscription_tier = "plus"
        current_user.subscription_status = "one_time"
        current_user.last_one_time_purchase_at = now
        current_user.last_one_time_external_id = tx.original_transaction_id
    else:
        current_user.subscription_current_period_end = tx.expires_date
        if tx.is_active:
            current_user.subscription_tier = "plus"
            current_user.subscription_status = "active"
        else:
            # Expired transaction (rare on a verify; possible during restore).
            current_user.subscription_tier = "free"
            current_user.subscription_status = "expired"

    if inserted is not None and body.coupon_id:
        await coupons_service.record_redemption(
            db,
            current_user,
            coupon_id=body.coupon_id,
            provider="apple",
            payment_external_id=tx.original_transaction_id,
            amount_paid_paise=0,  # Apple owns the actual price math
        )

    await db.commit()

    ent = await entitlements.get_entitlement(db, current_user)
    return ent.to_dto()


# ── 4b. Apple Promotional Offer signing (subscription discount codes) ──────

class RedeemOfferRequest(BaseModel):
    code: str


@router.post("/apple/redeem-offer")
async def apple_redeem_offer(
    body: RedeemOfferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a signed Apple Promotional Offer payload for StoreKit.

    Flow:
      1. iOS calls this with `code=EARLYSALE`.
      2. We validate the coupon (`subscription` target), look up the
         linked `apple_offer_id`, and sign a JWS-shaped payload.
      3. iOS passes the result into `Product.PurchaseOption.promotionalOffer(...)`.
      4. After StoreKit purchase, iOS hits `/billing/apple/verify` with
         `coupon_id` so we can record the redemption.
    """
    quote = await coupons_service.validate_and_quote(
        db, current_user, body.code, target="subscription"
    )
    if not quote.apple_offer_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "no_apple_offer",
                "message": "This code isn't available on iOS yet.",
            },
        )

    product_id = settings.APPLE_IAP_PRODUCT_ID_MONTHLY
    nonce = str(uuid.uuid4())
    timestamp_ms = int(time.time() * 1000)
    username_hash = hashlib.sha256(
        f"{current_user.id}".encode("utf-8")
    ).hexdigest()

    try:
        signature = apple_service.sign_promotional_offer(
            product_id=product_id,
            offer_id=quote.apple_offer_id,
            username_hash=username_hash,
            nonce=nonce,
            timestamp_ms=timestamp_ms,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "product_id": product_id,
        "offer_id": quote.apple_offer_id,
        "key_id": settings.APPLE_PROMO_OFFER_KEY_ID,
        "nonce": nonce,
        "timestamp_ms": timestamp_ms,
        "signature": signature,
        "username_hash": username_hash,
        "coupon_id": quote.coupon_id,
        "display_message": quote.display_message,
    }


# ── 5. Apple IAP: App Store Server Notifications V2 (webhook) ───────────────

@router.post("/apple/webhook")
async def apple_server_notification(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive and act on App Store Server Notifications V2.

    Apple posts ``{"signedPayload": "<JWS>"}``. The outer envelope is
    verified against Apple's root CA via the SDK; we then branch on
    ``notificationType`` (REFUND, EXPIRED, DID_CHANGE_RENEWAL_STATUS, etc.)
    and update the user's subscription state accordingly. ``notificationUUID``
    is the idempotency key.
    """
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    signed_payload = payload.get("signedPayload")
    if not signed_payload:
        raise HTTPException(status_code=400, detail="Missing signedPayload")

    try:
        notification = app_store_server.verify_notification(signed_payload)
    except app_store_server.VerificationException as exc:
        log.warning("Apple webhook signature verification failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_signature", "message": "Webhook signature invalid."},
        )

    notif_type = notification.rawNotificationType or (
        notification.notificationType.value if notification.notificationType else "UNKNOWN"
    )
    notif_subtype = notification.rawSubtype or (
        notification.subtype.value if notification.subtype else None
    )
    notif_uuid = notification.notificationUUID

    # Decode the inner transaction (if the notification carries one).
    tx = None
    inner_signed_tx = (
        notification.data.signedTransactionInfo if notification.data else None
    )
    if inner_signed_tx:
        try:
            tx = apple_service.decode_signed_transaction(inner_signed_tx)
        except app_store_server.VerificationException as exc:
            log.warning("Apple webhook: inner signedTransactionInfo invalid: %s", exc)
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_signature", "message": "Inner transaction signature invalid."},
            )

    # Find the user. For notifications without a transaction (e.g. summary-only)
    # or for original_transaction_ids we've never seen, we still log and ack.
    user = None
    if tx is not None:
        stmt = select(User).where(
            User.subscription_external_id == tx.original_transaction_id
        )
        user = (await db.execute(stmt)).scalars().first()

    if user is None:
        log.info(
            "apple webhook ignored: type=%s subtype=%s uuid=%s reason=%s",
            notif_type, notif_subtype, notif_uuid,
            "no inner tx" if tx is None else "no matching user",
        )
        return {"ok": True, "ignored": True}

    # Idempotency: dedupe on notificationUUID per Apple's recommendation.
    insert_stmt = (
        pg_insert(SubscriptionEvent)
        .values(
            user_id=user.id,
            provider="apple",
            event_id=notif_uuid or tx.transaction_id,
            event_type=notif_type,
            raw_payload={
                "notification_type": notif_type,
                "subtype": notif_subtype,
                "notification_uuid": notif_uuid,
                "transaction_id": tx.transaction_id,
                "original_transaction_id": tx.original_transaction_id,
                "environment": tx.environment,
                "expires_date": tx.expires_date.isoformat() if tx.expires_date else None,
            },
        )
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(SubscriptionEvent.id)
    )
    if (await db.execute(insert_stmt)).first() is None:
        return {"ok": True, "replay": True}

    # Always update period_end + environment from the verified transaction.
    user.subscription_environment = tx.environment
    if tx.expires_date is not None:
        user.subscription_current_period_end = tx.expires_date

    _apply_notification_state(user, notif_type, notif_subtype)

    await db.commit()
    return {"ok": True, "notification_type": notif_type, "subtype": notif_subtype}


# ── Notification-type → user state branching ─────────────────────────────────

# Refund / revoke variants — immediate downgrade.
_DOWNGRADE_NOW = {"REFUND", "REVOKE"}
# Lifecycle end — downgrade once the period has actually closed.
_EXPIRED_TYPES = {"EXPIRED", "GRACE_PERIOD_EXPIRED"}
# Active states — extend Plus.
_ACTIVATE_TYPES = {"SUBSCRIBED", "DID_RENEW", "OFFER_REDEEMED"}


def _apply_notification_state(
    user: User, notif_type: str, subtype: Optional[str]
) -> None:
    """Mutate ``user`` subscription fields based on the notification type.

    Idempotent: callers should already have deduped on notificationUUID, but
    repeating this function with the same args produces the same end state.
    """
    if notif_type in _DOWNGRADE_NOW:
        user.subscription_tier = "free"
        user.subscription_status = "canceled"
        return

    if notif_type in _EXPIRED_TYPES:
        user.subscription_tier = "free"
        user.subscription_status = "expired"
        return

    if notif_type in _ACTIVATE_TYPES:
        user.subscription_tier = "plus"
        user.subscription_status = "active"
        return

    if notif_type == "DID_CHANGE_RENEWAL_STATUS":
        if subtype == "AUTO_RENEW_DISABLED":
            # User opted out of renewal; Plus stays until period_end.
            user.subscription_status = "canceled"
        elif subtype == "AUTO_RENEW_ENABLED":
            user.subscription_status = "active"
        return

    if notif_type == "DID_FAIL_TO_RENEW":
        user.subscription_status = "past_due"
        return

    # CONSUMPTION_REQUEST, PRICE_INCREASE, TEST, MIGRATION, METADATA_UPDATE, etc.
    # — log only via the SubscriptionEvent audit row; no state change.
    log.info("apple webhook: no state change for type=%s subtype=%s", notif_type, subtype)


# ── 6. Cancel ────────────────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel the caller's active Razorpay subscription at cycle end.

    Apple-managed subscriptions cannot be canceled here — App Store rules
    require iOS users to manage via Settings → Apple ID. Trying to cancel
    an Apple subscription returns 400.
    """
    if current_user.subscription_provider != "razorpay" or not current_user.subscription_external_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "cancel_not_allowed",
                "message": "Manage your subscription via Settings on this platform.",
            },
        )
    try:
        razorpay_service.cancel_subscription(
            current_user.subscription_external_id, at_cycle_end=True
        )
    except Exception as exc:
        log.exception("razorpay cancel failed")
        raise HTTPException(status_code=502, detail="Could not cancel subscription") from exc

    # The webhook will set status=canceled. We optimistically reflect it now
    # so the UI can show "cancels on <date>" without waiting for the round-trip.
    current_user.subscription_status = "canceled"
    await db.commit()
    ent = await entitlements.get_entitlement(db, current_user)
    return ent.to_dto()
