"""Unit tests for app.services.payments.razorpay_service.

Every function is tested against a mock razorpay.Client so no real API calls
are made. Settings values are patched to known strings.
"""
import pytest
from unittest.mock import patch, MagicMock


# ── _client() factory ────────────────────────────────────────────────────────


class TestClientFactory:
    def test_missing_key_id_raises(self):
        mock_rz = MagicMock()
        with patch.dict("sys.modules", {"razorpay": mock_rz}):
            with patch("app.services.payments.razorpay_service.settings") as mock_settings:
                mock_settings.RAZORPAY_KEY_ID = None
                mock_settings.RAZORPAY_KEY_SECRET = "secret"
                from app.services.payments.razorpay_service import _client
                with pytest.raises(RuntimeError, match="RAZORPAY_KEY_ID"):
                    _client()

    def test_missing_key_secret_raises(self):
        mock_rz = MagicMock()
        with patch.dict("sys.modules", {"razorpay": mock_rz}):
            with patch("app.services.payments.razorpay_service.settings") as mock_settings:
                mock_settings.RAZORPAY_KEY_ID = "key_id"
                mock_settings.RAZORPAY_KEY_SECRET = None
                from app.services.payments.razorpay_service import _client
                with pytest.raises(RuntimeError, match="RAZORPAY_KEY_SECRET"):
                    _client()

    def test_valid_credentials_returns_client(self):
        mock_rz = MagicMock()
        mock_rz.Client.return_value = MagicMock()
        with patch.dict("sys.modules", {"razorpay": mock_rz}):
            with patch("app.services.payments.razorpay_service.settings") as mock_settings:
                mock_settings.RAZORPAY_KEY_ID = "key_test"
                mock_settings.RAZORPAY_KEY_SECRET = "secret_test"
                from app.services.payments.razorpay_service import _client
                client = _client()
                mock_rz.Client.assert_called_with(auth=("key_test", "secret_test"))
                assert client is not None


# ── create_monthly_subscription ──────────────────────────────────────────────


class TestCreateMonthlySubscription:
    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_missing_plan_id_raises(self, mock_settings, _mock_client):
        mock_settings.RAZORPAY_PLAN_ID_MONTHLY = None
        from app.services.payments.razorpay_service import create_monthly_subscription
        with pytest.raises(RuntimeError, match="RAZORPAY_PLAN_ID_MONTHLY"):
            create_monthly_subscription(user_email="a@b.com", user_name="A")

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_creates_subscription(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_PLAN_ID_MONTHLY = "plan_MONTHLY"
        mock_client = MagicMock()
        mock_client.subscription.create.return_value = {"id": "sub_123"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_monthly_subscription
        result = create_monthly_subscription(user_email="a@b.com", user_name="Alice")

        assert result == {"id": "sub_123"}
        payload = mock_client.subscription.create.call_args[0][0]
        assert payload["plan_id"] == "plan_MONTHLY"
        assert payload["notes"]["email"] == "a@b.com"
        assert payload["notes"]["name"] == "Alice"

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_creates_subscription_with_offer_id(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_PLAN_ID_MONTHLY = "plan_MONTHLY"
        mock_client = MagicMock()
        mock_client.subscription.create.return_value = {"id": "sub_456"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_monthly_subscription
        result = create_monthly_subscription(
            user_email="x@y.com", user_name="X", offer_id="offer_EARLY",
        )
        payload = mock_client.subscription.create.call_args[0][0]
        assert payload["offer_id"] == "offer_EARLY"
        assert result["id"] == "sub_456"

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_creates_subscription_with_custom_notes(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_PLAN_ID_MONTHLY = "plan_MONTHLY"
        mock_client = MagicMock()
        mock_client.subscription.create.return_value = {"id": "sub_789"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_monthly_subscription
        create_monthly_subscription(
            user_email="a@b.com", user_name=None,
            notes={"source": "ios"},
        )
        payload = mock_client.subscription.create.call_args[0][0]
        assert payload["notes"]["name"] == ""  # None → ""
        assert payload["notes"]["source"] == "ios"

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_creates_subscription_custom_total_count(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_PLAN_ID_MONTHLY = "plan_MONTHLY"
        mock_client = MagicMock()
        mock_client.subscription.create.return_value = {"id": "sub_tc"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_monthly_subscription
        create_monthly_subscription(
            user_email="a@b.com", user_name="B", total_count=12,
        )
        payload = mock_client.subscription.create.call_args[0][0]
        assert payload["total_count"] == 12


# ── create_one_time_order ────────────────────────────────────────────────────


class TestCreateOneTimeOrder:
    @patch("app.services.payments.razorpay_service._client")
    def test_creates_order(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": "order_1"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_one_time_order
        result = create_one_time_order(amount_paise=20000)

        assert result == {"id": "order_1"}
        payload = mock_client.order.create.call_args[0][0]
        assert payload["amount"] == 20000
        assert payload["currency"] == "INR"
        assert payload["payment_capture"] == 1

    @patch("app.services.payments.razorpay_service._client")
    def test_creates_order_with_receipt(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": "order_2"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import create_one_time_order
        create_one_time_order(
            amount_paise=5000, receipt="rcpt_abc",
            notes={"reason": "upgrade"},
        )
        payload = mock_client.order.create.call_args[0][0]
        assert payload["receipt"] == "rcpt_abc"
        assert payload["notes"]["reason"] == "upgrade"


# ── verify_order_signature ───────────────────────────────────────────────────


class TestVerifyOrderSignature:
    @patch("app.services.payments.razorpay_service._client")
    def test_valid_signature_returns_true(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = None
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import verify_order_signature
        assert verify_order_signature("ord_1", "pay_1", "sig_valid") is True

    @patch("app.services.payments.razorpay_service._client")
    def test_invalid_signature_returns_false(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.side_effect = Exception("bad sig")
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import verify_order_signature
        assert verify_order_signature("ord_1", "pay_1", "sig_bad") is False


# ── fetch_payment ────────────────────────────────────────────────────────────


class TestFetchPayment:
    @patch("app.services.payments.razorpay_service._client")
    def test_fetch_payment(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.payment.fetch.return_value = {"id": "pay_1", "status": "captured"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import fetch_payment
        result = fetch_payment("pay_1")
        assert result["status"] == "captured"
        mock_client.payment.fetch.assert_called_once_with("pay_1")


# ── cancel_subscription ─────────────────────────────────────────────────────


class TestCancelSubscription:
    @patch("app.services.payments.razorpay_service._client")
    def test_cancel_at_cycle_end(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.subscription.cancel.return_value = {"id": "sub_1", "status": "cancelled"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import cancel_subscription
        result = cancel_subscription("sub_1", at_cycle_end=True)
        assert result["status"] == "cancelled"
        mock_client.subscription.cancel.assert_called_once_with(
            "sub_1", {"cancel_at_cycle_end": 1},
        )

    @patch("app.services.payments.razorpay_service._client")
    def test_cancel_immediately(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.subscription.cancel.return_value = {"id": "sub_2"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import cancel_subscription
        cancel_subscription("sub_2", at_cycle_end=False)
        mock_client.subscription.cancel.assert_called_once_with(
            "sub_2", {"cancel_at_cycle_end": 0},
        )


# ── fetch_subscription ──────────────────────────────────────────────────────


class TestFetchSubscription:
    @patch("app.services.payments.razorpay_service._client")
    def test_fetch_subscription(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.subscription.fetch.return_value = {"id": "sub_1", "status": "active"}
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import fetch_subscription
        result = fetch_subscription("sub_1")
        assert result["status"] == "active"


# ── verify_webhook_signature ────────────────────────────────────────────────


class TestVerifyWebhookSignature:
    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_missing_webhook_secret_raises(self, mock_settings, _mock_client):
        mock_settings.RAZORPAY_WEBHOOK_SECRET = None

        from app.services.payments.razorpay_service import verify_webhook_signature
        with pytest.raises(RuntimeError, match="RAZORPAY_WEBHOOK_SECRET"):
            verify_webhook_signature(b"body", "sig")

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_valid_webhook_signature(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "whsec_test"
        mock_client = MagicMock()
        mock_client.utility.verify_webhook_signature.return_value = None
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import verify_webhook_signature
        assert verify_webhook_signature(b'{"event":"test"}', "sig_ok") is True
        mock_client.utility.verify_webhook_signature.assert_called_once_with(
            '{"event":"test"}', "sig_ok", "whsec_test",
        )

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_invalid_webhook_signature(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "whsec_test"
        mock_client = MagicMock()
        mock_client.utility.verify_webhook_signature.side_effect = Exception("bad")
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import verify_webhook_signature
        assert verify_webhook_signature(b"body", "bad_sig") is False

    @patch("app.services.payments.razorpay_service._client")
    @patch("app.services.payments.razorpay_service.settings")
    def test_webhook_signature_with_string_body(self, mock_settings, mock_client_fn):
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "whsec_test"
        mock_client = MagicMock()
        mock_client.utility.verify_webhook_signature.return_value = None
        mock_client_fn.return_value = mock_client

        from app.services.payments.razorpay_service import verify_webhook_signature
        assert verify_webhook_signature(b"raw_bytes", "sig") is True
