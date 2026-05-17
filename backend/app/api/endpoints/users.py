from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.db.session import get_db
from app.models.all_models import User
from app.core.security import get_password_hash, verify_password
from app.api.deps import get_current_user
from app.config.persona_catalog import Persona, get_catalog

router = APIRouter()


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
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
    await db.delete(current_user)
    await db.commit()
    return {"detail": "Account deleted"}
