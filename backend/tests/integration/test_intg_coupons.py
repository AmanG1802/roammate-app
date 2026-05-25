"""§2 Coupons — coupon validation via API and discount computation.

Uses the POST /billing/coupons/validate endpoint rather than calling the
service directly, because record_redemption relies on pg_insert
(PostgreSQL dialect) which is unavailable in the SQLite test harness.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.all_models import Coupon, CouponRedemption, User
from tests.conftest import TestSessionLocal


async def _seed_coupon(code="TEST10", **overrides):
    defaults = dict(
        code=code,
        is_active=True,
        discount_type="percent_off",
        discount_value=5000,  # 50 % in basis points
        applies_to="one_time",
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
    )
    defaults.update(overrides)
    async with TestSessionLocal() as s:
        c = Coupon(**defaults)
        s.add(c)
        await s.commit()
        return c.id, code


# ── Validation ────────────────────────────────────────────────────────────────

async def test_validate_coupon_returns_quote(client: AsyncClient, auth_headers):
    await _seed_coupon()
    resp = await client.post("/api/billing/coupons/validate", json={"code": "TEST10", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_amount_paise"] > 0


async def test_validate_coupon_not_found(client: AsyncClient, auth_headers):
    resp = await client.post("/api/billing/coupons/validate", json={"code": "NONEXISTENT", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_not_found"


async def test_validate_coupon_inactive(client: AsyncClient, auth_headers):
    await _seed_coupon("OFF10", is_active=False)
    resp = await client.post("/api/billing/coupons/validate", json={"code": "OFF10", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_inactive"


async def test_validate_coupon_expired(client: AsyncClient, auth_headers):
    await _seed_coupon("EXP", valid_until=datetime.utcnow() - timedelta(days=1))
    resp = await client.post("/api/billing/coupons/validate", json={"code": "EXP", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_expired"


async def test_validate_coupon_not_yet_active(client: AsyncClient, auth_headers):
    await _seed_coupon("FUTURE", valid_from=datetime.utcnow() + timedelta(days=5))
    resp = await client.post("/api/billing/coupons/validate", json={"code": "FUTURE", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_not_yet_active"


async def test_validate_coupon_wrong_target(client: AsyncClient, auth_headers):
    await _seed_coupon("ONETIMER", applies_to="one_time")
    resp = await client.post("/api/billing/coupons/validate", json={"code": "ONETIMER", "target": "subscription"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_wrong_target"


async def test_validate_coupon_already_redeemed(client: AsyncClient, auth_headers):
    cid, _ = await _seed_coupon("USED")
    me = (await client.get("/api/users/me", headers=auth_headers)).json()
    async with TestSessionLocal() as s:
        s.add(CouponRedemption(
            coupon_id=cid, user_id=me["id"],
            provider="internal_grant", amount_paid_paise=0,
        ))
        await s.commit()
    resp = await client.post("/api/billing/coupons/validate", json={"code": "USED", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "coupon_already_redeemed"


# ── Discount math (via API response) ─────────────────────────────────────────

async def test_flat_off_discount(client: AsyncClient, auth_headers):
    await _seed_coupon("FLAT200", discount_type="flat_off", discount_value=20000)
    resp = await client.post("/api/billing/coupons/validate", json={"code": "FLAT200", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["final_amount_paise"] < resp.json()["original_amount_paise"]


async def test_percent_off_discount(client: AsyncClient, auth_headers):
    await _seed_coupon("HALF", discount_type="percent_off", discount_value=5000)
    resp = await client.post("/api/billing/coupons/validate", json={"code": "HALF", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_amount_paise"] == body["original_amount_paise"] // 2


async def test_fixed_price_discount(client: AsyncClient, auth_headers):
    await _seed_coupon("FIX99", discount_type="fixed_price", discount_value=9900)
    resp = await client.post("/api/billing/coupons/validate", json={"code": "FIX99", "target": "one_time"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["final_amount_paise"] == 9900
