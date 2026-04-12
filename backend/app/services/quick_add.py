from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
from app.models.all_models import Event
from app.services.nlp_service import nlp_service
from app.services.google_maps import google_maps_service

class QuickAddService:
    async def process_text(
        self, 
        db: AsyncSession, 
        trip_id: int, 
        text: str
    ) -> Event:
        # 1. Parse intent with LLM
        parsed = await nlp_service.parse_quick_add(text)
        
        # 2. Resolve location with Google Maps
        location_data = await google_maps_service.find_place(parsed.get("title", text))
        
        # 3. Determine time
        # If the LLM didn't find a time, place it after the last event of the day
        start_time = None
        if parsed.get("start_iso"):
            start_time = datetime.fromisoformat(parsed["start_iso"])
        else:
            # Simple fallback for now: today at 10 AM if no other events
            start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

        duration = timedelta(minutes=parsed.get("duration_minutes", 60))

        # 4. Create and save event
        event = Event(
            trip_id=trip_id,
            title=location_data.get("name") if location_data else parsed.get("title", text),
            place_id=location_data.get("place_id") if location_data else None,
            lat=location_data.get("geometry", {}).get("location", {}).get("lat") if location_data else None,
            lng=location_data.get("geometry", {}).get("location", {}).get("lng") if location_data else None,
            start_time=start_time,
            end_time=start_time + duration,
            event_type=parsed.get("event_type", "activity")
        )
        
        db.add(event)
        await db.commit()
        return event

quick_add_service = QuickAddService()
