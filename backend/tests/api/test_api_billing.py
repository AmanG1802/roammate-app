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
    # Test 7a - POST - 400 Bad Request - Invalid signed transaction (ValueError)
    with patch("app.api.endpoints.billing.apple_service") as mock_apple:
        # Make the VerificationException attribute resolve to a real exception class
        mock_apple.VerificationException = type("VerificationException", (Exception,), {})
        mock_apple.decode_signed_transaction = MagicMock(side_effect=ValueError("bad token"))
        resp = await client.post("/api/billing/apple/verify", headers=auth_headers, json={
            "signed_transaction_info": "bad_jws",
        })
        assert resp.status_code == 400

    # Test 7b - POST - 422 Unprocessable Entity - Missing field
    resp = await client.post("/api/billing/apple/verify", headers=auth_headers, json={})
    assert resp.status_code == 422


async def test_verify_apple_invalid_signature_returns_400(
    client: AsyncClient, auth_headers: dict,
):
    """Test 7c - Tampered JWS surfaces as 400 with code=invalid_signature."""
    fake_exc = type("VerificationException", (Exception,), {})
    with patch("app.api.endpoints.billing.apple_service") as mock_apple:
        mock_apple.VerificationException = fake_exc
        mock_apple.decode_signed_transaction = MagicMock(
            side_effect=fake_exc("chain invalid")
        )
        resp = await client.post(
            "/api/billing/apple/verify",
            headers=auth_headers,
            json={"signed_transaction_info": "tampered_jws"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # detail may be nested dict; just confirm the code is present somewhere
        assert "invalid_signature" in resp.text


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


async def test_apple_webhook_invalid_signature_returns_400(client: AsyncClient):
    """Test 9c - Tampered signedPayload surfaces as 400."""
    fake_exc = type("VerificationException", (Exception,), {})
    with patch("app.api.endpoints.billing.app_store_server") as mock_ass:
        mock_ass.VerificationException = fake_exc
        mock_ass.verify_notification = MagicMock(side_effect=fake_exc("bad sig"))
        resp = await client.post(
            "/api/billing/apple/webhook",
            json={"signedPayload": "tampered"},
        )
        assert resp.status_code == 400
        assert "invalid_signature" in resp.text


def _mock_verified_notification(notif_type: str, subtype: str | None = None):
    """Build a MagicMock shaped like ResponseBodyV2DecodedPayload."""
    n = MagicMock()
    n.rawNotificationType = notif_type
    n.rawSubtype = subtype
    n.notificationUUID = f"uuid-{notif_type}-{subtype or 'none'}"
    n.data = MagicMock()
    n.data.signedTransactionInfo = "inner_jws"
    return n


def _mock_apple_transaction(original_id: str = "orig-1", expires_iso: str | None = None):
    """Build a MagicMock shaped like AppleTransaction."""
    tx = MagicMock()
    tx.transaction_id = "txn-1"
    tx.original_transaction_id = original_id
    tx.bundle_id = "app.roammate.ios"
    tx.product_id = "app.roammate.ios.plus.monthly"
    tx.environment = "Sandbox"
    if expires_iso:
        from datetime import datetime
        tx.expires_date = datetime.fromisoformat(expires_iso)
    else:
        tx.expires_date = None
    tx.is_one_time = False
    tx.is_active = True
    tx.is_valid_product = True
    return tx


async def test_apple_webhook_unknown_user_is_acked(client: AsyncClient):
    """Test 9d - Notification for unseen original_transaction_id is logged + acked."""
    fake_exc = type("VerificationException", (Exception,), {})
    with patch("app.api.endpoints.billing.app_store_server") as mock_ass, \
         patch("app.api.endpoints.billing.apple_service") as mock_apple:
        mock_ass.VerificationException = fake_exc
        mock_ass.verify_notification = MagicMock(
            return_value=_mock_verified_notification("REFUND")
        )
        mock_apple.VerificationException = fake_exc
        mock_apple.decode_signed_transaction = MagicMock(
            return_value=_mock_apple_transaction(original_id="never-seen")
        )
        resp = await client.post(
            "/api/billing/apple/webhook",
            json={"signedPayload": "ok"},
        )
        assert resp.status_code == 200
        assert resp.json().get("ignored") is True


# ── POST /api/billing/cancel ──────────────────────────────────────────────

async def test_cancel_subscription_post(client: AsyncClient, auth_headers: dict):
    # Test 10a - POST - 400 Bad Request - No active Razorpay subscription to cancel
    resp = await client.post("/api/billing/cancel", headers=auth_headers)
    assert resp.status_code == 400

    # Test 10b - POST - 401 Unauthorized - No auth (clear cookies)
    resp = await client.post("/api/billing/cancel", headers=NO_AUTH)
    assert resp.status_code == 401
