from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.all_models import IdeaBinItem
from app.services.google_maps import google_maps_service

class IdeaBinService:
    async def ingest_from_text(
        self, 
        db: AsyncSession, 
        trip_id: int, 
        text: str, 
        source_url: Optional[str] = None
    ) -> List[IdeaBinItem]:
        # Simple parsing for now: split by newline or comma
        lines = [l.strip() for l in text.replace(',', '\n').split('\n') if l.strip()]
        
        results = []
        for line in lines:
            place_data = await google_maps_service.find_place(line)
            
            if place_data:
                item = IdeaBinItem(
                    trip_id=trip_id,
                    title=place_data.get("name", line),
                    place_id=place_data.get("place_id"),
                    lat=place_data.get("geometry", {}).get("location", {}).get("lat"),
                    lng=place_data.get("geometry", {}).get("location", {}).get("lng"),
                    url_source=source_url
                )
                db.add(item)
                results.append(item)
        
        await db.commit()
        return results

idea_bin_service = IdeaBinService()
