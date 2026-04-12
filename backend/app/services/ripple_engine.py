from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.all_models import Event

class RippleEngine:
    async def shift_itinerary(
        self,
        db: AsyncSession,
        trip_id: int,
        delta_minutes: int,
        start_from_time: Optional[datetime] = None
    ) -> List[Event]:
        """
        Shifts all events in a trip by a certain number of minutes.
        If start_from_time is provided, only events starting after this time are shifted.
        """
        if not start_from_time:
            start_from_time = datetime.now()

        # Fetch all events for the trip starting after start_from_time
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.trip_id == trip_id,
                    Event.start_time >= start_from_time,
                    Event.is_locked == False # Don't shift locked events
                )
            )
            .order_by(Event.start_time)
        )
        
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        delta = timedelta(minutes=delta_minutes)
        
        for event in events:
            event.start_time += delta
            event.end_time += delta
            
        await db.commit()
        return list(events)

ripple_engine = RippleEngine()
