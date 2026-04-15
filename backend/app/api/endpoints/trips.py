from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.db.session import get_db
from app.models.all_models import Trip, TripMember, User, IdeaBinItem as IdeaBinItemModel
from app.schemas.trip import (
    Trip as TripSchema, TripCreate, IngestRequest, IdeaBinItem,
    TripMemberOut, InviteRequest,
)
from app.services.idea_bin import idea_bin_service
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TripSchema])
async def get_my_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all trips where the current user is a member.
    """
    stmt = (
        select(Trip)
        .join(TripMember)
        .where(TripMember.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=TripSchema)
async def create_trip(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new trip and add the current user as the owner.
    """
    trip = Trip(
        name=trip_in.name,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        created_by_id=current_user.id
    )
    db.add(trip)
    await db.flush() # Get the ID
    
    # Add creator as owner member
    member = TripMember(
        trip_id=trip.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member)
    await db.commit()
    await db.refresh(trip)
    return trip

@router.get("/{trip_id}", response_model=TripSchema)
async def get_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")
    
    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.get("/{trip_id}/ideas", response_model=List[IdeaBinItem])
async def get_idea_bin(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(IdeaBinItemModel).where(IdeaBinItemModel.trip_id == trip_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{trip_id}/members", response_model=List[TripMemberOut])
async def get_trip_members(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all members of a trip (with user details). Caller must be a member."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = (
        select(TripMember)
        .where(TripMember.trip_id == trip_id)
        .options(selectinload(TripMember.user))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{trip_id}/invite", response_model=TripMemberOut, status_code=201)
async def invite_to_trip(
    trip_id: int,
    invite: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a registered user to the trip by email. Caller must be owner/editor."""
    # Verify requester is an owner or editor
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="Not authorized to invite members")

    # Find the invitee by email
    stmt = select(User).where(User.email == invite.email)
    invitee = (await db.execute(stmt)).scalars().first()
    if not invitee:
        raise HTTPException(status_code=404, detail="No account found with that email")

    # Check for duplicate membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == invitee.id,
    )
    if (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=409, detail="User is already a member of this trip")

    new_member = TripMember(trip_id=trip_id, user_id=invitee.id, role="editor")
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    # Re-fetch with user relationship loaded
    stmt = (
        select(TripMember)
        .where(TripMember.id == new_member.id)
        .options(selectinload(TripMember.user))
    )
    return (await db.execute(stmt)).scalars().first()


@router.delete("/{trip_id}/ideas/{idea_id}", status_code=204)
async def delete_idea(
    trip_id: int,
    idea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an idea from the bin (called when idea is moved to the itinerary)."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(IdeaBinItemModel).where(
        IdeaBinItemModel.id == idea_id,
        IdeaBinItemModel.trip_id == trip_id,
    )
    item = (await db.execute(stmt)).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Idea not found")

    await db.delete(item)
    await db.commit()


@router.post("/{trip_id}/ingest", response_model=List[IdeaBinItem])
async def ingest_to_idea_bin(
    trip_id: int, 
    request: IngestRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to edit this trip")

    try:
        items = await idea_bin_service.ingest_from_text(
            db=db, 
            trip_id=trip_id, 
            text=request.text, 
            source_url=request.source_url
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
