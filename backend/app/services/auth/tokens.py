"""Access + refresh token issuance, verification, and rotation.

Access tokens are short-lived JWTs (HS256). Claims:
    sub  – user id (string)
    ver  – user.auth_version at issue time; bump invalidates outstanding tokens
    iat / exp

Refresh tokens are opaque random URL-safe strings, stored hashed (sha256) in
the refresh_token table. Each use rotates: the old row is marked consumed and
a new row is issued with parent_id set. Reuse of a consumed/revoked token
revokes the entire chain (token-theft detection).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Optional

from jose import jwt, JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.all_models import RefreshToken, User
from app.utils.tz import utc_now


# ── Access tokens ────────────────────────────────────────────────────────────


def create_access_token(user: User) -> str:
    now = utc_now()
    payload = {
        "sub": str(user.id),
        "ver": int(user.auth_version or 1),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns claims or raises JWTError."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


# ── Refresh tokens ───────────────────────────────────────────────────────────


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    db: AsyncSession,
    user: User,
    *,
    device_label: Optional[str] = None,
    parent_id: Optional[int] = None,
) -> tuple[str, RefreshToken]:
    raw = secrets.token_urlsafe(32)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash(raw),
        device_label=device_label,
        parent_id=parent_id,
        expires_at=utc_now() + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
    )
    db.add(row)
    await db.flush()
    return raw, row


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
) -> tuple[User, str, RefreshToken]:
    """Validate a presented refresh token and rotate it.

    Returns (user, new_raw, new_row). Raises ValueError on any failure
    (unknown / expired / revoked / reused). On reuse-of-consumed, the entire
    rotation chain rooted at this token's parent is revoked.
    """
    token_hash = _hash(raw_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise ValueError("unknown refresh token")

    now = utc_now()
    if row.revoked_at is not None or row.expires_at <= now:
        # Reuse / replay attempt — kill the chain.
        await _revoke_chain(db, row)
        raise ValueError("refresh token revoked or expired")

    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if user is None:
        raise ValueError("user gone")

    # Mark old row revoked + issue new one with parent_id link
    row.revoked_at = now
    row.last_used_at = now
    new_raw, new_row = await issue_refresh_token(
        db, user, device_label=row.device_label, parent_id=row.id
    )
    return user, new_raw, new_row


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    token_hash = _hash(raw_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )


async def _revoke_chain(db: AsyncSession, row: RefreshToken) -> None:
    """Walk to the root of the rotation chain and revoke everything we issued
    for this user since — defensive when a consumed token is replayed."""
    await revoke_all_for_user(db, row.user_id)


__all__ = [
    "create_access_token",
    "decode_access_token",
    "issue_refresh_token",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "revoke_all_for_user",
]
