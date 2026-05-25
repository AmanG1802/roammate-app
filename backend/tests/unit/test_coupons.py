"""Unit tests for app.services.coupons — pure computation helpers.

Tests _target_matches, _compute_final, _display_message, _original_price_paise.
The async functions (validate_and_quote, record_redemption) require DB.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.services.coupons import (
    _target_matches,
    _compute_final,
    _display_message,
    _original_price_paise,
    _raise,
    CouponQuote,
)


def _make_coupon(
    applies_to: str = "any",
    discount_type: str = "flat_off",
    discount_value: int = 5000,
    code: str = "TEST50",
    razorpay_offer_id: str | None = None,
    apple_offer_id: str | None = None,
):
    coupon = MagicMock()
    coupon.applies_to = applies_to
    coupon.discount_type = discount_type
    coupon.discount_value = discount_value
    coupon.code = code
    coupon.razorpay_offer_id = razorpay_offer_id
    coupon.apple_offer_id = apple_offer_id
    return coupon


class TestTargetMatches:
    def test_target_matches(self):
        # Test 1a - "any" coupon matches one_time
        coupon = _make_coupon(applies_to="any")
        assert _target_matches(coupon, "one_time") is True

        # Test 1b - "any" coupon matches subscription
        assert _target_matches(coupon, "subscription") is True

        # Test 1c - "one_time" coupon matches one_time target
        coupon = _make_coupon(applies_to="one_time")
        assert _target_matches(coupon, "one_time") is True

        # Test 1d - "one_time" coupon does NOT match subscription target
        assert _target_matches(coupon, "subscription") is False

        # Test 1e - "subscription_first_cycle" coupon matches subscription target
        coupon = _make_coupon(applies_to="subscription_first_cycle")
        assert _target_matches(coupon, "subscription") is True

        # Test 1f - "subscription_first_cycle" coupon does NOT match one_time target
        assert _target_matches(coupon, "one_time") is False


class TestComputeFinal:
    def test_flat_off(self):
        # Test 1a - Flat ₹50 off a ₹200 price (20000 paise, discount_value=5000)
        coupon = _make_coupon(discount_type="flat_off", discount_value=5000)
        discount, final = _compute_final(20000, coupon)
        assert discount == 5000
        assert final == 15000

        # Test 1b - Flat discount larger than original clamps to original
        coupon = _make_coupon(discount_type="flat_off", discount_value=30000)
        discount, final = _compute_final(20000, coupon)
        assert discount == 20000
        assert final == 0

    def test_percent_off(self):
        # Test 1c - 50% off (discount_value=5000 basis points) on ₹200 (20000 paise)
        coupon = _make_coupon(discount_type="percent_off", discount_value=5000)
        discount, final = _compute_final(20000, coupon)
        assert discount == 10000
        assert final == 10000

        # Test 1d - 100% off (10000 basis points) makes final 0
        coupon = _make_coupon(discount_type="percent_off", discount_value=10000)
        discount, final = _compute_final(20000, coupon)
        assert discount == 20000
        assert final == 0

        # Test 1e - 25% off (2500 basis points) on ₹149 (14900 paise)
        coupon = _make_coupon(discount_type="percent_off", discount_value=2500)
        discount, final = _compute_final(14900, coupon)
        expected_discount = (14900 * 2500) // 10000
        assert discount == expected_discount
        assert final == 14900 - expected_discount

    def test_fixed_price(self):
        # Test 1f - Fixed price ₹99 (9900 paise) on ₹200 (20000 paise)
        coupon = _make_coupon(discount_type="fixed_price", discount_value=9900)
        discount, final = _compute_final(20000, coupon)
        assert final == 9900
        assert discount == 20000 - 9900

        # Test 1g - Fixed price higher than original clamps to original
        coupon = _make_coupon(discount_type="fixed_price", discount_value=30000)
        discount, final = _compute_final(20000, coupon)
        assert final == 20000
        assert discount == 0

    def test_unknown_type(self):
        # Test 1h - Unknown discount_type raises HTTPException
        coupon = _make_coupon(discount_type="BOGUS")
        with pytest.raises(HTTPException):
            _compute_final(20000, coupon)


class TestDisplayMessage:
    def test_display_message(self):
        # Test 1a - Fixed price message
        coupon = _make_coupon(discount_type="fixed_price", code="FIRST99")
        msg = _display_message(coupon, 10100, 9900)
        assert "₹99" in msg
        assert "FIRST99" in msg

        # Test 1b - Free coupon (final=0)
        coupon = _make_coupon(discount_type="flat_off", code="FREE30")
        msg = _display_message(coupon, 20000, 0)
        assert "free" in msg.lower()
        assert "FREE30" in msg

        # Test 1c - Flat off with remaining price
        coupon = _make_coupon(discount_type="flat_off", code="SAVE50")
        msg = _display_message(coupon, 5000, 15000)
        assert "₹50" in msg
        assert "off" in msg
        assert "SAVE50" in msg


class TestOriginalPricePaise:
    @patch("app.services.coupons.settings")
    def test_original_price_paise(self, mock_settings):
        # Test 1a - One-time target uses PLUS_ONETIME_PRICE_INR
        mock_settings.PLUS_ONETIME_PRICE_INR = 200
        mock_settings.PLUS_MONTHLY_PRICE_INR = 149
        assert _original_price_paise("one_time") == 200 * 100

        # Test 1b - Subscription target uses PLUS_MONTHLY_PRICE_INR
        assert _original_price_paise("subscription") == 149 * 100


class TestRaise:
    def test_raise(self):
        # Test 1a - Raises HTTPException with specified status code
        with pytest.raises(HTTPException) as exc_info:
            _raise("coupon_not_found", "That code isn't valid", 400)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "coupon_not_found"
        assert exc_info.value.detail["message"] == "That code isn't valid"

        # Test 1b - Default status is 400
        with pytest.raises(HTTPException) as exc_info:
            _raise("test_code", "test message")
        assert exc_info.value.status_code == 400


class TestCouponQuote:
    def test_coupon_quote_to_dto(self):
        # Test 1a - to_dto returns all fields as dict
        quote = CouponQuote(
            coupon_id=1,
            code="TEST",
            applies_to="one_time",
            original_amount_paise=20000,
            discount_amount_paise=5000,
            final_amount_paise=15000,
            razorpay_offer_id=None,
            apple_offer_id="offer_123",
            display_message="TEST applied",
        )
        dto = quote.to_dto()
        assert dto["coupon_id"] == 1
        assert dto["code"] == "TEST"
        assert dto["applies_to"] == "one_time"
        assert dto["original_amount_paise"] == 20000
        assert dto["discount_amount_paise"] == 5000
        assert dto["final_amount_paise"] == 15000
        assert dto["razorpay_offer_id"] is None
        assert dto["apple_offer_id"] == "offer_123"
        assert dto["display_message"] == "TEST applied"
