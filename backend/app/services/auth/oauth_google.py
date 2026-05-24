"""Verify a Google ID token (issued by Google Identity Services on web or
GoogleSignIn-iOS on iOS) and return the canonical {sub, email, email_verified,
name, picture} payload."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings


@dataclass
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]


async def verify(id_token_str: str, *, platform: str = "web") -> GoogleIdentity:
    """Validate an ID token. `platform` selects the expected audience.

    Raises ValueError on any verification failure.

    The actual token check is CPU-bound RSA signature verification (~10-50ms);
    it runs in a worker thread via ``asyncio.to_thread`` so it never blocks the
    event loop under load. See docs/[31] A8.
    """
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:
        raise ValueError("google-auth not installed on the server") from exc

    if platform == "ios":
        audience = settings.GOOGLE_OAUTH_CLIENT_ID_IOS
    else:
        audience = settings.GOOGLE_OAUTH_CLIENT_ID_WEB
    if not audience:
        raise ValueError(f"GOOGLE_OAUTH_CLIENT_ID for platform={platform} not configured")

    try:
        info = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            id_token_str, google_requests.Request(), audience,
        )
    except Exception as exc:  # google-auth raises a variety of errors
        raise ValueError(f"invalid Google ID token: {exc}") from exc

    if info.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        raise ValueError("unexpected issuer")

    email = info.get("email")
    sub = info.get("sub")
    if not email or not sub:
        raise ValueError("Google token missing email or sub")

    return GoogleIdentity(
        sub=sub,
        email=email.lower(),
        email_verified=bool(info.get("email_verified", False)),
        name=info.get("name"),
        picture=info.get("picture"),
    )
