"""Role gating helpers for trip-scoped actions."""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.all_models import TripMember

VOTE_ROLES = {"admin", "view_with_vote"}
ADMIN_ONLY = {"admin"}


async def get_trip_member(db: AsyncSession, trip_id: int, user_id: int) -> TripMember | None:
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == user_id,
        TripMember.status == "accepted",
    )
    return (await db.execute(stmt)).scalars().first()


async def require_trip_member(db: AsyncSession, trip_id: int, user_id: int) -> TripMember:
    m = await get_trip_member(db, trip_id, user_id)
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this trip")
    return m


async def require_trip_admin(db: AsyncSession, trip_id: int, user_id: int) -> TripMember:
    m = await require_trip_member(db, trip_id, user_id)
    if m.role not in ADMIN_ONLY:
        raise HTTPException(status_code=403, detail="Trip admin role required")
    return m


async def require_vote_role(db: AsyncSession, trip_id: int, user_id: int) -> TripMember:
    m = await require_trip_member(db, trip_id, user_id)
    if m.role not in VOTE_ROLES:
        raise HTTPException(status_code=403, detail="Your role is view-only and cannot vote")
    return m
