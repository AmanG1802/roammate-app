"""App Store Server API + JWS verification.

Thin wrapper over Apple's official ``app-store-server-library`` (Python SDK).
Owns two lazy singletons:

  * ``SignedDataVerifier`` — verifies JWS/JWE signatures on StoreKit 2
    transaction blobs and SSN V2 webhook envelopes against Apple's root CA.
  * ``AppStoreServerAPIClient`` — JWT-authenticated REST client for the
    App Store Server API (lookups, refund history, etc.).

All Apple-specific configuration is consumed from ``app.core.config.settings``;
nothing is hardcoded.

The SDK does not bundle Apple's root certificate — download it once from
https://www.apple.com/certificateauthority/AppleRootCA-G3.cer and point
``APPLE_ROOT_CA_PATH`` at it. The path is loaded lazily so tests that mock
this module don't require the file to exist.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from appstoreserverlibrary.api_client import AppStoreServerAPIClient
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import (
    JWSTransactionDecodedPayload,
)
from appstoreserverlibrary.models.ResponseBodyV2DecodedPayload import (
    ResponseBodyV2DecodedPayload,
)
from appstoreserverlibrary.signed_data_verifier import (
    SignedDataVerifier,
    VerificationException,
)

from app.core.config import settings

log = logging.getLogger(__name__)

__all__ = [
    "VerificationException",
    "JWSTransactionDecodedPayload",
    "ResponseBodyV2DecodedPayload",
    "get_verifier",
    "get_api_client",
    "verify_transaction_jws",
    "verify_notification",
    "lookup_subscription_statuses",
]


def _environment() -> Environment:
    return Environment.SANDBOX if settings.APPLE_USE_SANDBOX else Environment.PRODUCTION


def _require(name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(
            f"{name} is not configured. Set it in the environment "
            f"(see .env.example for App Store Server API setup)."
        )
    return value


def _load_root_certs() -> list[bytes]:
    if settings.APPLE_ROOT_CA_B64:
        import base64
        return [base64.b64decode(settings.APPLE_ROOT_CA_B64)]
    path = _require("APPLE_ROOT_CA_PATH", settings.APPLE_ROOT_CA_PATH)
    with open(path, "rb") as f:
        return [f.read()]


def _load_signing_key() -> bytes:
    if settings.APPLE_PRIVATE_KEY_B64:
        import base64
        return base64.b64decode(settings.APPLE_PRIVATE_KEY_B64)
    path = _require("APPLE_PRIVATE_KEY_PATH", settings.APPLE_PRIVATE_KEY_PATH)
    with open(path, "rb") as f:
        return f.read()


@lru_cache(maxsize=1)
def get_verifier() -> SignedDataVerifier:
    """Lazy-built ``SignedDataVerifier``.

    Online checks (CRL/OCSP) are disabled for latency; chain validation
    against the bundled root cert is sufficient for our threat model.
    """
    return SignedDataVerifier(
        root_certificates=_load_root_certs(),
        enable_online_checks=False,
        environment=_environment(),
        bundle_id=_require("APPLE_BUNDLE_ID", settings.APPLE_BUNDLE_ID),
    )


@lru_cache(maxsize=1)
def get_api_client() -> AppStoreServerAPIClient:
    """Lazy-built ``AppStoreServerAPIClient`` for server-to-Apple calls."""
    return AppStoreServerAPIClient(
        signing_key=_load_signing_key(),
        key_id=_require("APPLE_KEY_ID", settings.APPLE_KEY_ID),
        issuer_id=_require("APPLE_ISSUER_ID", settings.APPLE_ISSUER_ID),
        bundle_id=_require("APPLE_BUNDLE_ID", settings.APPLE_BUNDLE_ID),
        environment=_environment(),
    )


def verify_transaction_jws(jws: str) -> JWSTransactionDecodedPayload:
    """Verify and decode a StoreKit 2 ``jwsRepresentation`` blob.

    Raises ``VerificationException`` if the signature chain, bundle id, or
    environment doesn't match.
    """
    return get_verifier().verify_and_decode_signed_transaction(jws)


def verify_notification(signed_payload: str) -> ResponseBodyV2DecodedPayload:
    """Verify and decode an SSN V2 ``signedPayload`` envelope."""
    return get_verifier().verify_and_decode_notification(signed_payload)


def lookup_subscription_statuses(original_transaction_id: str):
    """Fetch latest subscription status for an ``originalTransactionId``.

    Returns the SDK's ``StatusResponse``. Use this when the webhook delivery
    is suspect or you need ground-truth state (e.g. before honoring a refund
    downgrade). Apple's API may raise; callers should handle gracefully.
    """
    return get_api_client().get_all_subscription_statuses(original_transaction_id)
