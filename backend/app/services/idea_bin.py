from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.all_models import IdeaBinItem
from app.services.google_maps import get_google_maps_service

google_maps_service = get_google_maps_service()


class IdeaBinService:
    async def ingest_from_text(
        self,
        db: AsyncSession,
        trip_id: int,
        text: str,
        source_url: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> List[IdeaBinItem]:
        lines = [l.strip() for l in text.replace(',', '\n').split('\n') if l.strip()]

        results = []
        for line in lines:
            try:
                place_data = await google_maps_service.find_place(line)
            except Exception:
                place_data = None

            if place_data:
                display = place_data.get("displayName") or {}
                title = display.get("text") if isinstance(display, dict) else None
                pid = place_data.get("id") or place_data.get("place_id")
                location = place_data.get("location") or {}
                geo = place_data.get("geometry", {}).get("location", {})
                item = IdeaBinItem(
                    trip_id=trip_id,
                    title=title or place_data.get("name") or line,
                    place_id=pid,
                    lat=location.get("latitude") or geo.get("lat"),
                    lng=location.get("longitude") or geo.get("lng"),
                    added_by=added_by,
                )
                db.add(item)
                results.append(item)
            else:
                item = IdeaBinItem(
                    trip_id=trip_id,
                    title=line,
                    added_by=added_by,
                )
                db.add(item)
                results.append(item)

        await db.commit()
        for item in results:
            await db.refresh(item)
        return results

idea_bin_service = IdeaBinService()
