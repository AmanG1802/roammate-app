"""API tests for billing.py — status, Razorpay subscription/one-time, Apple IAP, coupons, cancel."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

NO_AUTH = {"Cookie": "", "Authorization": ""}


def _mock_entitlement():
    ent = MagicMock()
    ent.to_dto = MagicMock(return_value={
        "tier": "free",
        "brainstorm_remaining": 5,
        "concierge_remaining": 5,
    })
    return ent


# ── GET /api/billing/status ────────────────────────────────────────────────

async def test_get_billing_status_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Returns entitlement for free user
    resp = await client.get("/api/billing/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data

    # Test 1b - GET - 401 Unauthorized - No auth (clear cookies)
    resp = await client.get("/api/billing/status", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/billing/razorpay/subscription ────────────────────────────────

async def test_create_razorpay_subscription_post(client: AsyncClient, auth_headers: dict):
    # Test 2a - POST - 503 Service Unavailable - Razorpay not configured (RuntimeError)
    with patch("app.api.endpoints.billing.razorpay_service") as mock_rz:
        mock_rz.create_monthly_subscription = MagicMock(side_effect=RuntimeError("Not configured"))
        resp = await client.post("/api/billing/razorpay/subscription", headers=auth_headers, json={})
        assert resp.status_code == 503

    # Test 2b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post("/api/billing/razorpay/subscription", json={}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/billing/razorpay/one-time ────────────────────────────────────

async def test_create_one_time_purchase_post(client: AsyncClient, auth_headers: dict):
    # Test 3a - POST - 503 Service Unavailable - Razorpay not configured
    with patch("app.api.endpoints.billing.razorpay_service") as mock_rz:
        mock_rz.create_one_time_order = MagicMock(side_effect=RuntimeError("Not configured"))
        resp = await client.post("/api/billing/razorpay/one-time", headers=auth_headers, json={})
        assert resp.status_code == 503

    # Test 3b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post("/api/billing/razorpay/one-time", json={}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/billing/razorpay/one-time/verify ─────────────────────────────

async def test_verify_one_time_purchase_post(client: AsyncClient, auth_headers: dict):
    # Test 4a - POST - 400 Bad Request - Invalid signature
    with patch("app.api.endpoints.billing.razorpay_service") as mock_rz:
        mock_rz.verify_order_signature = MagicMock(return_value=False)
        resp = await client.post("/api/billing/razorpay/one-time/verify", headers=auth_headers, json={
            "order_id": "order_abc", "payment_id": "pay_abc", "signature": "bad_sig",
        })
        assert resp.status_code == 400

    # Test 4b - POST - 422 Unprocessable Entity - Missing required fields
    resp = await client.post("/api/billing/razorpay/one-time/verify", headers=auth_headers, json={})
    assert resp.status_code == 422


# ── POST /api/billing/razorpay/webhook ─────────────────────────────────────

async def test_razorpay_webhook_post(client: AsyncClient):
    # Test 5a - POST - 400 Bad Request - Missing signature header
    resp = await client.post("/api/billing/razorpay/webhook", content=b'{}')
    assert resp.status_code == 400

    # Test 5b - POST - 400 Bad Request - Invalid signature
    with patch("app.api.endpoints.billing.razorpay_service") as mock_rz:
        mock_rz.verify_webhook_signature = MagicMock(return_value=False)
        resp = await client.post(
            "/api/billing/razorpay/webhook",
            content=b'{}',
            headers={"X-Razorpay-Signature": "bad"},
        )
        assert resp.status_code == 400


# ── POST /api/billing/coupons/validate ─────────────────────────────────────

async def test_validate_coupon_post(client: AsyncClient, auth_headers: dict):
    # Test 6a - POST - 422 Unprocessable Entity - Missing fields
    resp = await client.post("/api/billing/coupons/validate", headers=auth_headers, json={})
    assert resp.status_code == 422

    # Test 6b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post(
        "/api/billing/coupons/validate",
        json={"code": "TEST", "target": "subscription"},
        headers=NO_AUTH,
    )
    assert resp.status_code == 401


# ── POST /api/billing/apple/verify ─────────────────────────────────────────

async def test_verify_apple_transaction_post(client: AsyncClient, auth_headers: dict):
    # Test 7a - POST - 400 Bad Request - Invalid signed transaction
    with patch("app.api.endpoints.billing.apple_service") as mock_apple:
        mock_apple.decode_signed_transaction = MagicMock(side_effect=ValueError("bad token"))
        resp = await client.post("/api/billing/apple/verify", headers=auth_headers, json={
            "signed_transaction_info": "bad_jws",
        })
        assert resp.status_code == 400

    # Test 7b - POST - 422 Unprocessable Entity - Missing field
    resp = await client.post("/api/billing/apple/verify", headers=auth_headers, json={})
    assert resp.status_code == 422


# ── POST /api/billing/apple/redeem-offer ───────────────────────────────────

async def test_apple_redeem_offer_post(client: AsyncClient, auth_headers: dict):
    # Test 8a - POST - 422 Unprocessable Entity - Missing code
    resp = await client.post("/api/billing/apple/redeem-offer", headers=auth_headers, json={})
    assert resp.status_code == 422

    # Test 8b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post(
        "/api/billing/apple/redeem-offer",
        json={"code": "TEST"},
        headers=NO_AUTH,
    )
    assert resp.status_code == 401


# ── POST /api/billing/apple/webhook ────────────────────────────────────────

async def test_apple_server_notification_post(client: AsyncClient):
    # Test 9a - POST - 400 Bad Request - Missing signedPayload
    resp = await client.post("/api/billing/apple/webhook", json={})
    assert resp.status_code == 400

    # Test 9b - POST - 400 Bad Request - Invalid JSON
    resp = await client.post("/api/billing/apple/webhook", content=b'not json')
    assert resp.status_code == 400


# ── POST /api/billing/cancel ──────────────────────────────────────────────

async def test_cancel_subscription_post(client: AsyncClient, auth_headers: dict):
    # Test 10a - POST - 400 Bad Request - No active Razorpay subscription to cancel
    resp = await client.post("/api/billing/cancel", headers=auth_headers)
    assert resp.status_code == 400

    # Test 10b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post("/api/billing/cancel", headers=NO_AUTH)
    assert resp.status_code == 401
