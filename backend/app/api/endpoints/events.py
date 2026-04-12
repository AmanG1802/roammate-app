from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.event import Event, RippleRequest
from app.schemas.trip import IngestRequest
from app.services.ripple_engine import ripple_engine
from app.services.quick_add import quick_add_service

router = APIRouter()

@router.get("/", response_model=List[Event])
async def get_events(db: AsyncSession = Depends(get_db)):
    # Mocking for now
    return []

@router.post("/ripple/{trip_id}", response_model=List[Event])
async def trigger_ripple_engine(
    trip_id: int,
    request: RippleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers the Ripple Engine to shift all subsequent events in an itinerary.
    Useful for "Running Late" or manual time adjustments.
    """
    try:
        updated_events = await ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=request.delta_minutes,
            start_from_time=request.start_from_time
        )
        return updated_events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick-add/{trip_id}", response_model=Event)
async def quick_add_event(
    trip_id: int,
    request: IngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    NLP Quick Add: Parses text like "Colosseum tour at 2pm" and creates a scheduled event.
    """
    try:
        event = await quick_add_service.process_text(
            db=db,
            trip_id=trip_id,
            text=request.text
        )
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
