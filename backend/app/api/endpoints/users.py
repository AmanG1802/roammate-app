from typing import Any, List, Optional
import logging
import zoneinfo
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.db.session import get_db
from app.models.all_models import (
    User, UserIdentity, Trip, Group, GroupMember, TripMember,
    IdeaVote, EventVote, Notification,
)
from app.core.security import get_password_hash, verify_password
from app.api.deps import get_current_user
from app.config.persona_catalog import Persona, get_catalog
from app.services.auth import oauth_apple
from app.services.auth.email import send_password_changed_notice, send_account_deleted_notice

log = logging.getLogger(__name__)

_VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AUD", "JPY", "CAD", "SGD"}
_TRAVEL_BLURB_MAX = 280

router = APIRouter()


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    personas: Optional[list] = None
    avatar_url: Optional[str] = None
    home_city: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    travel_blurb: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PersonasUpdate(BaseModel):
    personas: list[str]


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    home_city: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    travel_blurb: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None


# Legacy /register and /login removed — see /api/auth/* for the replacement.


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # --- Field validation ---
    if profile_in.travel_blurb is not None and len(profile_in.travel_blurb) > _TRAVEL_BLURB_MAX:
        raise HTTPException(status_code=422, detail=f"travel_blurb must be {_TRAVEL_BLURB_MAX} characters or fewer")
    if profile_in.timezone is not None and profile_in.timezone not in zoneinfo.available_timezones():
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {profile_in.timezone!r}")
    if profile_in.currency is not None and profile_in.currency not in _VALID_CURRENCIES:
        raise HTTPException(status_code=422, detail=f"Unsupported currency: {profile_in.currency!r}. Must be one of {sorted(_VALID_CURRENCIES)}")

    password_changed = False
    if profile_in.password:
        if not profile_in.current_password:
            raise HTTPException(status_code=400, detail="Current password required to set a new password")
        if not current_user.hashed_password or not verify_password(profile_in.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_user.hashed_password = get_password_hash(profile_in.password)
        # Invalidate every outstanding access + refresh token.
        current_user.auth_version = (current_user.auth_version or 1) + 1
        from app.services.auth.tokens import revoke_all_for_user
        await revoke_all_for_user(db, current_user.id)
        password_changed = True

    if profile_in.name is not None:
        current_user.name = profile_in.name
    if profile_in.avatar_url is not None:
        current_user.avatar_url = profile_in.avatar_url
    if profile_in.home_city is not None:
        current_user.home_city = profile_in.home_city
    if profile_in.timezone is not None:
        current_user.timezone = profile_in.timezone
    if profile_in.currency is not None:
        current_user.currency = profile_in.currency
    if profile_in.travel_blurb is not None:
        current_user.travel_blurb = profile_in.travel_blurb

    await db.commit()
    await db.refresh(current_user)

    if password_changed:
        send_password_changed_notice(current_user.email, current_user.name)

    return current_user


@router.get("/personas/catalog")
async def get_personas_catalog() -> list[dict]:
    return get_catalog()


@router.get("/me/personas")
async def get_my_personas(current_user: User = Depends(get_current_user)):
    return {"personas": current_user.personas}


@router.put("/me/personas")
async def update_my_personas(
    body: PersonasUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    valid_values = {p.value for p in Persona}
    invalid = [s for s in body.personas if s not in valid_values]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown persona slug(s): {invalid}",
        )

    current_user.personas = body.personas
    await db.commit()
    await db.refresh(current_user)
    return {"personas": current_user.personas}


@router.delete("/me")
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id
    # Capture before deletion so we can send the confirmation email after commit.
    user_email = current_user.email
    user_name = current_user.name

    # Cancel active Razorpay subscription so the user isn't billed after deletion.
    if (
        current_user.subscription_provider == "razorpay"
        and current_user.subscription_external_id
        and current_user.subscription_status in ("active", "authenticated")
    ):
        try:
            from app.services.payments import razorpay_service
            razorpay_service.cancel_subscription(current_user.subscription_external_id)
        except Exception as exc:
            log.warning("Razorpay cancel failed for user %s on account deletion: %s", uid, exc)

    # Revoke Apple refresh token before deleting the record (Guideline 5.1.1(v)).
    apple_identity = (await db.execute(
        select(UserIdentity).where(
            UserIdentity.user_id == uid,
            UserIdentity.provider == "apple",
        )
    )).scalar_one_or_none()
    if apple_identity and apple_identity.apple_refresh_token:
        await oauth_apple.revoke_token(apple_identity.apple_refresh_token)

    # Explicit FK-safe cleanup for tables that lack ON DELETE CASCADE in the DB.
    # Order matters: child rows before parent rows.
    await db.execute(delete(IdeaVote).where(IdeaVote.user_id == uid))
    await db.execute(delete(EventVote).where(EventVote.user_id == uid))
    # Nullify actor on notifications sent by this user; delete ones addressed to them.
    await db.execute(update(Notification).where(Notification.actor_id == uid).values(actor_id=None))
    await db.execute(delete(Notification).where(Notification.user_id == uid))
    await db.execute(delete(TripMember).where(TripMember.user_id == uid))
    await db.execute(delete(GroupMember).where(GroupMember.user_id == uid))
    await db.execute(update(Trip).where(Trip.created_by_id == uid).values(created_by_id=None))
    await db.execute(update(Group).where(Group.owner_id == uid).values(owner_id=None))
    await db.delete(current_user)
    await db.commit()

    send_account_deleted_notice(user_email, user_name)
    return {"detail": "Account deleted"}
