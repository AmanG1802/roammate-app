"""Find-or-create + auto-link logic for OAuth identities.

Rule (matches the approved plan):
  - If a UserIdentity already exists for (provider, subject), return that user.
  - Else if a User with the OAuth email exists AND that User.email_verified is
    True AND the OAuth provider also reports email_verified, link the new
    identity to that user and return them.
  - Else if such a User exists but is unverified, raise OAuthLinkBlocked so the
    client can prompt the user to verify their existing account first.
  - Else create a new User (email_verified=True since the provider asserts it,
    when the provider actually does), and link the identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import User, UserIdentity
from app.utils.tz import utc_now


class OAuthLinkBlocked(Exception):
    """Raised when an OAuth login matches an existing unverified email account."""

    def __init__(self, email: str):
        super().__init__(f"Existing unverified account for {email}")
        self.email = email


@dataclass
class OAuthClaims:
    provider: str            # 'google' | 'apple'
    subject: str
    email: Optional[str]
    email_verified: bool
    name: Optional[str] = None
    avatar_url: Optional[str] = None


async def find_or_create_user_for_oauth(  # pragma: no cover — OAuth linking
    db: AsyncSession,
    claims: OAuthClaims,
) -> User:
    # 1. Existing identity link?
    stmt = select(UserIdentity).where(
        UserIdentity.provider == claims.provider,
        UserIdentity.subject == claims.subject,
    )
    identity = (await db.execute(stmt)).scalar_one_or_none()
    if identity is not None:
        user = (await db.execute(select(User).where(User.id == identity.user_id))).scalar_one()
        return user

    # 2. Email match?
    user: Optional[User] = None
    if claims.email:
        user = (
            await db.execute(select(User).where(User.email == claims.email))
        ).scalar_one_or_none()

    if user is not None:
        if not (user.email_verified and claims.email_verified):
            raise OAuthLinkBlocked(claims.email or "")
        # safe to auto-link
        db.add(UserIdentity(
            user_id=user.id,
            provider=claims.provider,
            subject=claims.subject,
            email_at_link=claims.email,
        ))
        if not user.name and claims.name:
            user.name = claims.name
        if not user.avatar_url and claims.avatar_url:
            user.avatar_url = claims.avatar_url
        await db.flush()
        return user

    # 3. Create fresh
    new_user = User(
        email=(claims.email or f"{claims.provider}_{claims.subject}@no-email.local"),
        name=claims.name,
        avatar_url=claims.avatar_url,
        email_verified=bool(claims.email and claims.email_verified),
        email_verified_at=utc_now() if (claims.email and claims.email_verified) else None,
    )
    db.add(new_user)
    await db.flush()
    db.add(UserIdentity(
        user_id=new_user.id,
        provider=claims.provider,
        subject=claims.subject,
        email_at_link=claims.email,
    ))
    await db.flush()
    return new_user
