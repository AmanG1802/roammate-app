from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.all_models import Trip, TripMember, User, IdeaBinItem as IdeaBinItemModel
from app.schemas.trip import Trip as TripSchema, TripCreate, IngestRequest, IdeaBinItem
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
