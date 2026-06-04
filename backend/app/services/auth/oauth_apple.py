"""Verify an Apple ID token (Sign in with Apple).

Apple does not expose a Python SDK; we fetch JWKS from Apple's well-known
endpoint, cache the keys, and validate the token signature + claims ourselves.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx
from jose import jwt
from jose.utils import base64url_decode

from app.core.config import settings


APPLE_ISSUER = "https://appleid.apple.com"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

_keys_cache: dict = {"fetched_at": 0.0, "keys": []}
_KEYS_TTL_S = 60 * 60 * 6  # 6 hours


@dataclass
class AppleIdentity:
    sub: str
    email: Optional[str]
    email_verified: bool


async def _get_keys() -> list[dict]:  # pragma: no cover — Apple JWKS fetch
    now = time.time()
    if _keys_cache["keys"] and now - _keys_cache["fetched_at"] < _KEYS_TTL_S:
        return _keys_cache["keys"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(APPLE_KEYS_URL)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
    _keys_cache["keys"] = keys
    _keys_cache["fetched_at"] = now
    return keys


def _allowed_audiences(platform: str) -> list[str]:
    if platform == "ios":
        return [a for a in [settings.APPLE_SIGNIN_BUNDLE_ID] if a]
    return [a for a in [settings.APPLE_SIGNIN_SERVICE_ID] if a]


async def verify(id_token_str: str, *, platform: str = "web") -> AppleIdentity:  # pragma: no cover
    audiences = _allowed_audiences(platform)
    if not audiences:
        raise ValueError(
            f"Apple sign-in audience for platform={platform} not configured "
            "(set APPLE_SIGNIN_BUNDLE_ID or APPLE_SIGNIN_SERVICE_ID)"
        )

    try:
        unverified_header = jwt.get_unverified_header(id_token_str)
    except Exception as exc:
        raise ValueError(f"malformed Apple token: {exc}") from exc

    kid = unverified_header.get("kid")
    keys = await _get_keys()
    jwk = next((k for k in keys if k.get("kid") == kid), None)
    if jwk is None:
        # Force refresh once in case Apple rotated keys
        _keys_cache["fetched_at"] = 0
        keys = await _get_keys()
        jwk = next((k for k in keys if k.get("kid") == kid), None)
    if jwk is None:
        raise ValueError("Apple signing key not found")

    try:
        claims = jwt.decode(
            id_token_str,
            jwk,
            algorithms=[unverified_header.get("alg", "RS256")],
            audience=audiences,
            issuer=APPLE_ISSUER,
            options={"verify_at_hash": False},
        )
    except Exception as exc:
        raise ValueError(f"invalid Apple ID token: {exc}") from exc

    sub = claims.get("sub")
    if not sub:
        raise ValueError("Apple token missing sub")

    email = claims.get("email")
    # Apple sometimes returns email_verified as the string "true"
    raw_verified = claims.get("email_verified", False)
    email_verified = raw_verified is True or str(raw_verified).lower() == "true"

    return AppleIdentity(
        sub=sub,
        email=email.lower() if email else None,
        email_verified=email_verified,
    )


# silence unused-import lint when type checkers prune base64url_decode
_ = base64url_decode
