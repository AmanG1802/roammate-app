from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.all_models import Event as EventModel, TripMember, User
from app.schemas.event import Event, RippleRequest
from app.schemas.trip import IngestRequest
from app.services.ripple_engine import ripple_engine
from app.services.quick_add import quick_add_service
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Event])
async def get_events(
    trip_id: int = Query(..., description="Trip to fetch events for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all events for a trip the current user is a member of."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(EventModel).where(EventModel.trip_id == trip_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/ripple/{trip_id}", response_model=List[Event])
async def trigger_ripple_engine(
    trip_id: int,
    request: RippleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger the Ripple Engine to shift all subsequent events.
    Used for "Running Late" or manual time adjustments.
    """
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    try:
        updated_events = await ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=request.delta_minutes,
            start_from_time=request.start_from_time,
        )
        return updated_events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-add/{trip_id}", response_model=Event)
async def quick_add_event(
    trip_id: int,
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    NLP Quick Add: Parses text like "Colosseum tour at 2pm" and creates a scheduled event.
    """
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    try:
        event = await quick_add_service.process_text(
            db=db,
            trip_id=trip_id,
            text=request.text,
        )
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
