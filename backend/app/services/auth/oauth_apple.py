"""Verify an Apple ID token (Sign in with Apple).

Apple does not expose a Python SDK; we fetch JWKS from Apple's well-known
endpoint, cache the keys, and validate the token signature + claims ourselves.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from jose import jwt
from jose.utils import base64url_decode

from app.core.config import settings

log = logging.getLogger(__name__)


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
    # python-jose accepts a string or None, not a list
    audience = audiences[0]

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
            audience=audience,
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


# ── SIWA token exchange + revocation ─────────────────────────────────────────

APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"


def _generate_client_secret() -> str:
    """Create the short-lived ES256 JWT that Apple requires as a client secret.

    Requires APPLE_SIGNIN_TEAM_ID, APPLE_SIGNIN_KEY_ID, and
    APPLE_SIGNIN_PRIVATE_KEY_PATH to be set in the environment.
    """
    team_id = settings.APPLE_SIGNIN_TEAM_ID
    key_id = settings.APPLE_SIGNIN_KEY_ID
    key_path = settings.APPLE_SIGNIN_PRIVATE_KEY_PATH
    bundle_id = settings.APPLE_SIGNIN_BUNDLE_ID

    if not all([team_id, key_id, key_path, bundle_id]):
        raise RuntimeError(
            "SIWA client secret generation requires APPLE_SIGNIN_TEAM_ID, "
            "APPLE_SIGNIN_KEY_ID, APPLE_SIGNIN_PRIVATE_KEY_PATH, and "
            "APPLE_SIGNIN_BUNDLE_ID to be set."
        )

    pem = open(key_path).read()  # type: ignore[arg-type]
    now = int(time.time())
    return jwt.encode(
        {"iss": team_id, "iat": now, "exp": now + 15777000, "aud": APPLE_ISSUER, "sub": bundle_id},
        pem,
        algorithm="ES256",
        headers={"kid": key_id},
    )


async def exchange_code(authorization_code: str) -> Optional[str]:
    """Exchange a one-time SIWA authorization code for a long-lived refresh token.

    Returns the refresh token string, or None if the exchange fails non-fatally
    (e.g. code already consumed). Logs the error but does not raise so that the
    sign-in itself is not blocked.
    """
    if not settings.APPLE_SIGNIN_KEY_ID or not settings.APPLE_SIGNIN_PRIVATE_KEY_PATH:
        log.warning("SIWA key not configured — skipping token exchange")
        return None
    try:
        client_secret = _generate_client_secret()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                APPLE_TOKEN_URL,
                data={
                    "client_id": settings.APPLE_SIGNIN_BUNDLE_ID,
                    "client_secret": client_secret,
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code == 200:
            return resp.json().get("refresh_token")
        log.warning("Apple token exchange returned %s: %s", resp.status_code, resp.text)
        return None
    except Exception as exc:
        log.warning("Apple token exchange failed: %s", exc)
        return None


async def revoke_token(refresh_token: str) -> None:
    """Revoke an Apple refresh token (Guideline 5.1.1(v) — account deletion).

    Best-effort: logs on failure but does not raise so the account deletion
    can still proceed.
    """
    if not settings.APPLE_SIGNIN_KEY_ID or not settings.APPLE_SIGNIN_PRIVATE_KEY_PATH:
        log.warning("SIWA key not configured — skipping token revocation")
        return
    try:
        client_secret = _generate_client_secret()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                APPLE_REVOKE_URL,
                data={
                    "client_id": settings.APPLE_SIGNIN_BUNDLE_ID,
                    "client_secret": client_secret,
                    "token": refresh_token,
                    "token_type_hint": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code not in (200, 204):
            log.warning("Apple token revocation returned %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        log.warning("Apple token revocation failed: %s", exc)
