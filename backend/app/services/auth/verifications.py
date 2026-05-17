"""Email-verification + password-reset token issuance and consumption.

Tokens are random URL-safe strings; only the sha256 hash is stored. The raw
token is included in the email link.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import EmailVerification, PasswordReset, User
from app.utils.tz import utc_now


VERIFY_TTL = timedelta(hours=24)
RESET_TTL = timedelta(hours=1)


def _hash(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


async def issue_verification(
    db: AsyncSession,
    user: User,
    *,
    email: str,
    purpose: str = "signup",
) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(EmailVerification(
        token_hash=_hash(raw),
        user_id=user.id,
        email=email,
        purpose=purpose,
        expires_at=utc_now() + VERIFY_TTL,
    ))
    await db.flush()
    return raw


async def consume_verification(
    db: AsyncSession,
    raw_token: str,
) -> Optional[EmailVerification]:
    row = (await db.execute(
        select(EmailVerification).where(EmailVerification.token_hash == _hash(raw_token))
    )).scalar_one_or_none()
    if row is None:
        return None
    if row.consumed_at is not None or row.expires_at <= utc_now():
        return None
    row.consumed_at = utc_now()
    await db.flush()
    return row


async def issue_reset(db: AsyncSession, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(PasswordReset(
        token_hash=_hash(raw),
        user_id=user.id,
        expires_at=utc_now() + RESET_TTL,
    ))
    await db.flush()
    return raw


async def consume_reset(db: AsyncSession, raw_token: str) -> Optional[PasswordReset]:
    row = (await db.execute(
        select(PasswordReset).where(PasswordReset.token_hash == _hash(raw_token))
    )).scalar_one_or_none()
    if row is None:
        return None
    if row.consumed_at is not None or row.expires_at <= utc_now():
        return None
    row.consumed_at = utc_now()
    await db.flush()
    return row
