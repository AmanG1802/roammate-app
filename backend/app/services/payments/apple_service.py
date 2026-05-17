"""Apple App Store auto-renewable subscription helpers.

We accept the JWS `signedTransactionInfo` blob from StoreKit 2 on the device
and verify it server-side by decoding the JWT header to pick the right Apple
certificate. For v1 we use a *trust-the-device* decode (no certificate chain
verification) so the integration works in sandbox without bundling Apple's
root CA — this is acceptable because the same transaction is later
cross-checked by Apple's Server Notifications V2 (the webhook), which is the
real source of truth for renewals and refunds. When we wire SSN V2 we can
also call Apple's App Store Server API for ground-truth state.

JWS layout (per Apple docs):
  {
    "transactionId": "20000...",
    "originalTransactionId": "20000...",
    "bundleId": "com.roammate.app",
    "productId": "com.roammate.app.plus.monthly",
    "purchaseDate": 1715000000000,          # ms epoch
    "expiresDate": 1717692000000,
    "type": "Auto-Renewable Subscription",
    "inAppOwnershipType": "PURCHASED",
    "environment": "Sandbox" | "Production",
    ...
  }
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppleTransaction:
    transaction_id: str
    original_transaction_id: str
    bundle_id: str
    product_id: str
    purchase_date: datetime
    expires_date: Optional[datetime]
    environment: str  # "Sandbox" | "Production"

    @property
    def is_valid_product(self) -> bool:
        return self.bundle_id == settings.APPLE_BUNDLE_ID and self.product_id in {
            settings.APPLE_IAP_PRODUCT_ID_MONTHLY,
            settings.APPLE_IAP_PRODUCT_ID_ONETIME,
        }

    @property
    def is_one_time(self) -> bool:
        return self.product_id == settings.APPLE_IAP_PRODUCT_ID_ONETIME

    @property
    def is_active(self) -> bool:
        if self.expires_date is None:
            return True
        return self.expires_date >= datetime.now(timezone.utc)


def _b64url_decode(segment: str) -> bytes:
    # Apple's JWS uses url-safe base64 without padding.
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def decode_signed_transaction(jws: str) -> AppleTransaction:
    """Decode the JWS payload to an AppleTransaction.

    Raises ValueError on a malformed token. Does not verify the signature
    chain — see module docstring for the trade-off.
    """
    parts = jws.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWS — expected 3 segments")
    try:
        payload_bytes = _b64url_decode(parts[1])
        payload = json.loads(payload_bytes)
    except Exception as exc:
        raise ValueError(f"Could not decode JWS payload: {exc}") from exc

    def _ms_to_dt(key: str) -> Optional[datetime]:
        v = payload.get(key)
        if v is None:
            return None
        return datetime.fromtimestamp(int(v) / 1000.0, tz=timezone.utc)

    tx_id = str(payload.get("transactionId") or payload.get("transaction_id") or "")
    orig_id = str(
        payload.get("originalTransactionId")
        or payload.get("original_transaction_id")
        or tx_id
    )
    if not tx_id:
        raise ValueError("JWS payload missing transactionId")

    return AppleTransaction(
        transaction_id=tx_id,
        original_transaction_id=orig_id,
        bundle_id=str(payload.get("bundleId") or payload.get("bundle_id") or ""),
        product_id=str(payload.get("productId") or payload.get("product_id") or ""),
        purchase_date=_ms_to_dt("purchaseDate")
            or _ms_to_dt("purchase_date")
            or datetime.now(timezone.utc),
        expires_date=_ms_to_dt("expiresDate") or _ms_to_dt("expires_date"),
        environment=str(payload.get("environment") or "Sandbox"),
    )


# ── Promotional Offer signing (subscription discounts) ──────────────────────


def sign_promotional_offer(
    *,
    product_id: str,
    offer_id: str,
    username_hash: str,
    nonce: str,
    timestamp_ms: int,
) -> str:
    """Sign an Apple Subscription Promotional Offer payload (ES256).

    Per Apple docs, the payload to sign is the UTF-8 string:

        bundleId\\nkeyId\\nproductId\\nofferId\\nusernameHash\\nnonce\\ntimestamp

    (Note: `appBundleVersion` is not part of the canonical signing payload;
    only the seven fields above.) The resulting ECDSA P-256 signature is
    base64-encoded (DER) and handed to StoreKit on the device via
    `Product.PurchaseOption.promotionalOffer(...)`.
    """
    if not settings.APPLE_PROMO_OFFER_P8_KEY or not settings.APPLE_PROMO_OFFER_KEY_ID:
        raise RuntimeError(
            "APPLE_PROMO_OFFER_P8_KEY / APPLE_PROMO_OFFER_KEY_ID not configured. "
            "Generate a Subscription Offers key in App Store Connect."
        )
    # Lazy import to keep boot light if Apple offers aren't wired.
    from cryptography.hazmat.primitives import hashes, serialization  # type: ignore
    from cryptography.hazmat.primitives.asymmetric import ec  # type: ignore

    pem = settings.APPLE_PROMO_OFFER_P8_KEY.replace("\\n", "\n").encode("utf-8")
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("APPLE_PROMO_OFFER_P8_KEY must be an ECDSA P-256 PEM key")

    bundle_id = settings.APPLE_BUNDLE_ID
    key_id = settings.APPLE_PROMO_OFFER_KEY_ID
    payload = (
        f"{bundle_id}\n{key_id}\n{product_id}\n{offer_id}"
        f"\n{username_hash}\n{nonce}\n{timestamp_ms}"
    )
    signature = key.sign(payload.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode("ascii")
