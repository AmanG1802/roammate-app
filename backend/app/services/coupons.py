"""Coupon / promo-code service for Roammate Plus.

Two flavors of coupon at launch:
  - "one_time": discount applied to a ₹200 one-time Plus purchase. Backend
    computes final price; if it lands at 0 we grant Plus directly without
    touching Razorpay/Apple.
  - "subscription_first_cycle": delivered via Razorpay Offer (web) or Apple
    Promotional Offer (iOS) — the payment provider does the discount math.
    Backend only records redemption on first successful charge.

Coupons are per-user single-use (UNIQUE(coupon_id, user_id)) and time-bounded
via valid_from / valid_until.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.all_models import Coupon, CouponRedemption, User

log = logging.getLogger(__name__)

CouponTarget = Literal["one_time", "subscription"]


@dataclass
class CouponQuote:
    coupon_id: int
    code: str
    applies_to: str
    original_amount_paise: int
    discount_amount_paise: int
    final_amount_paise: int
    razorpay_offer_id: Optional[str]
    apple_offer_id: Optional[str]
    display_message: str

    def to_dto(self) -> dict:
        return asdict(self)


def _raise(code: str, message: str, status: int = 400) -> None:
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _target_matches(coupon: Coupon, target: CouponTarget) -> bool:
    if coupon.applies_to == "any":
        return True
    if target == "one_time":
        return coupon.applies_to == "one_time"
    if target == "subscription":
        return coupon.applies_to == "subscription_first_cycle"
    return False


def _compute_final(original_paise: int, coupon: Coupon) -> tuple[int, int]:
    """Returns (discount_paise, final_paise). Final is clamped to >= 0."""
    if coupon.discount_type == "flat_off":
        discount = min(coupon.discount_value, original_paise)
    elif coupon.discount_type == "percent_off":
        # discount_value is basis points (5000 = 50%)
        discount = (original_paise * coupon.discount_value) // 10_000
        discount = min(discount, original_paise)
    elif coupon.discount_type == "fixed_price":
        # discount_value IS the final price
        final = min(coupon.discount_value, original_paise)
        return max(original_paise - final, 0), final
    else:
        _raise("coupon_unknown_type", f"Unknown discount_type: {coupon.discount_type}")
    return discount, max(original_paise - discount, 0)


def _display_message(coupon: Coupon, discount_paise: int, final_paise: int) -> str:
    rupees = lambda p: f"₹{p // 100}"  # noqa: E731
    if coupon.discount_type == "fixed_price":
        return f"First charge {rupees(final_paise)} with {coupon.code}"
    if final_paise == 0:
        return f"{coupon.code} applied — free 30-day Plus on us"
    return f"{coupon.code} applied — {rupees(discount_paise)} off"


async def _get_coupon_by_code(db: AsyncSession, code: str) -> Coupon:
    code = (code or "").strip().upper()
    if not code:
        _raise("coupon_not_found", "Enter a coupon code")
    stmt = select(Coupon).where(Coupon.code == code)
    coupon: Optional[Coupon] = (await db.execute(stmt)).scalar_one_or_none()
    if not coupon:
        _raise("coupon_not_found", "That code isn't valid")
    return coupon  # type: ignore[return-value]


async def _already_redeemed(db: AsyncSession, coupon_id: int, user_id: int) -> bool:
    stmt = select(CouponRedemption.id).where(
        CouponRedemption.coupon_id == coupon_id,
        CouponRedemption.user_id == user_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def _original_price_paise(target: CouponTarget) -> int:
    if target == "one_time":
        return settings.PLUS_ONETIME_PRICE_INR * 100
    return settings.PLUS_MONTHLY_PRICE_INR * 100


async def validate_and_quote(
    db: AsyncSession,
    user: User,
    code: str,
    target: CouponTarget,
) -> CouponQuote:
    """Validate a coupon for this user + target without reserving it.

    Raises HTTPException(400) with detail.code in:
      - "coupon_not_found"
      - "coupon_inactive"
      - "coupon_expired" / "coupon_not_yet_active"
      - "coupon_wrong_target"
      - "coupon_already_redeemed"
    """
    coupon = await _get_coupon_by_code(db, code)
    if not coupon.is_active:
        _raise("coupon_inactive", "This code is no longer active")

    now = _now()
    if coupon.valid_from and coupon.valid_from > now:
        _raise("coupon_not_yet_active", "This code isn't active yet")
    if coupon.valid_until and coupon.valid_until < now:
        _raise("coupon_expired", "This code has expired")

    if not _target_matches(coupon, target):
        _raise(
            "coupon_wrong_target",
            "This code can't be used on the selected plan",
        )

    if await _already_redeemed(db, coupon.id, user.id):
        _raise("coupon_already_redeemed", "You've already used this code")

    original = _original_price_paise(target)
    discount, final = _compute_final(original, coupon)
    return CouponQuote(
        coupon_id=coupon.id,
        code=coupon.code,
        applies_to=coupon.applies_to,
        original_amount_paise=original,
        discount_amount_paise=discount,
        final_amount_paise=final,
        razorpay_offer_id=coupon.razorpay_offer_id,
        apple_offer_id=coupon.apple_offer_id,
        display_message=_display_message(coupon, discount, final),
    )


async def record_redemption(
    db: AsyncSession,
    user: User,
    coupon_id: int,
    provider: str,
    payment_external_id: Optional[str],
    amount_paid_paise: int,
) -> None:
    """Insert a redemption row idempotently.

    On conflict (user already has a redemption for this coupon) the insert is
    a no-op — this lets webhook handlers safely re-process events. Caller is
    responsible for transaction boundaries.
    """
    stmt = (
        pg_insert(CouponRedemption)
        .values(
            coupon_id=coupon_id,
            user_id=user.id,
            provider=provider,
            payment_external_id=payment_external_id,
            amount_paid_paise=amount_paid_paise,
        )
        .on_conflict_do_nothing(constraint="uq_coupon_redemption_coupon_user")
    )
    await db.execute(stmt)


async def get_coupon(db: AsyncSession, coupon_id: int) -> Optional[Coupon]:
    return (await db.execute(select(Coupon).where(Coupon.id == coupon_id))).scalar_one_or_none()
