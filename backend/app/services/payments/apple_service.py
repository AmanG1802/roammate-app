"""Apple App Store auto-renewable subscription helpers.

JWS blobs from StoreKit 2 (``jwsRepresentation``) and SSN V2 envelopes
(``signedPayload``) are cryptographically verified against Apple's root CA
via ``app.services.payments.app_store_server`` before any business logic
runs. A forged or tampered JWS will raise ``VerificationException`` from
this module's ``decode_signed_transaction``.

Expected ``bundleId`` / ``productId`` values are resolved from environment
settings (see ``app.core.config``); nothing is hardcoded.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.payments import app_store_server
from app.services.payments.app_store_server import (  # re-exported for callers
    VerificationException,
)

log = logging.getLogger(__name__)

__all__ = [
    "AppleTransaction",
    "VerificationException",
    "decode_signed_transaction",
    "sign_promotional_offer",
]


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


def _ms_to_dt(ms: Optional[int]) -> Optional[datetime]:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc)


def decode_signed_transaction(jws: str) -> AppleTransaction:
    """Verify and decode a StoreKit 2 ``jwsRepresentation``.

    Signature chain, bundle id, and environment are all checked by the SDK.
    Raises ``VerificationException`` on tampered / invalid input, or
    ``ValueError`` if the verified payload is missing the transaction id
    (should never happen in well-formed Apple data, but guarded for clarity).
    """
    payload = app_store_server.verify_transaction_jws(jws)

    tx_id = str(payload.transactionId or "")
    if not tx_id:
        raise ValueError("Verified JWS payload missing transactionId")

    purchase_dt = _ms_to_dt(payload.purchaseDate) or datetime.now(timezone.utc)
    env_value = payload.rawEnvironment or (
        payload.environment.value if payload.environment is not None else "Sandbox"
    )

    return AppleTransaction(
        transaction_id=tx_id,
        original_transaction_id=str(payload.originalTransactionId or tx_id),
        bundle_id=str(payload.bundleId or ""),
        product_id=str(payload.productId or ""),
        purchase_date=purchase_dt,
        expires_date=_ms_to_dt(payload.expiresDate),
        environment=str(env_value),
    )


# ── Promotional Offer signing (subscription discounts) ──────────────────────


def sign_promotional_offer(  # pragma: no cover — requires Apple P8 key
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
