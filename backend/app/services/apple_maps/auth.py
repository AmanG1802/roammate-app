"""JWT token generation for the Apple Maps Server API.

Apple requires a short-lived ES256 JWT signed with the MapKit private key
(.p8 file) issued from the Apple Developer portal.  Tokens are valid for
up to 30 minutes; we cache them for 25 minutes to avoid clock-skew issues.

Requires the ``PyJWT`` and ``cryptography`` packages (both already in the
project's dependency tree).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import jwt

log = logging.getLogger(__name__)

_TOKEN_LIFETIME_S = 25 * 60  # 25 min (Apple allows up to 30 min)


class AppleMapsTokenProvider:
    """Generates and caches Apple Maps Server API access tokens."""

    def __init__(self, team_id: str, key_id: str, private_key_path: str) -> None:
        self._team_id = team_id
        self._key_id = key_id
        self._private_key = Path(private_key_path).read_text()
        self._cached_token: Optional[str] = None
        self._expires_at: float = 0.0

    def token(self) -> str:
        now = time.time()
        if self._cached_token and now < self._expires_at:
            return self._cached_token

        payload = {
            "iss": self._team_id,
            "iat": int(now),
            "exp": int(now) + _TOKEN_LIFETIME_S + 300,
        }
        headers = {
            "kid": self._key_id,
            "typ": "JWT",
            "alg": "ES256",
        }
        self._cached_token = jwt.encode(
            payload, self._private_key, algorithm="ES256", headers=headers
        )
        self._expires_at = now + _TOKEN_LIFETIME_S
        log.debug("Generated new Apple Maps JWT (expires in %ds)", _TOKEN_LIFETIME_S)
        return self._cached_token
