import re

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.all_models import IdeaBinItem
from app.services.google_maps import get_google_maps_service

# Module-level alias so existing tests that patch
# ``app.services.idea_bin.google_maps_service.find_place`` keep working.
google_maps_service = get_google_maps_service()

_TIME_RE = re.compile(
    r'(?:at\s+|@\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{2}:\d{2})',
    re.IGNORECASE,
)


def _extract_time_hint(text: str) -> Optional[str]:
    """Pull a time fragment like '2pm' or '14:00' from free-form text."""
    m = _TIME_RE.search(text)
    return m.group(1).strip() if m else None


def _strip_time_hint(text: str) -> str:
    """Remove the time portion so the title stays clean."""
    cleaned = re.sub(r'\s+(?:at|@)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\d{2}:\d{2}', '', cleaned)
    return cleaned.strip()


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
            time_hint = _extract_time_hint(line)
            clean_line = _strip_time_hint(line) or line

            try:
                place_data = await google_maps_service.find_place(clean_line)
            except Exception:
                place_data = None
            
            if place_data:
                # Tolerant of both V1 (legacy) and V2 (new) response shapes:
                #   V1: name, place_id, geometry.location.{lat,lng}
                #   V2: displayName.text, id, location.{latitude,longitude}
                display = place_data.get("displayName") or {}
                title = display.get("text") if isinstance(display, dict) else None
                pid = place_data.get("id") or place_data.get("place_id")
                location = place_data.get("location") or {}
                geo = place_data.get("geometry", {}).get("location", {})
                item = IdeaBinItem(
                    trip_id=trip_id,
                    title=title or place_data.get("name") or clean_line,
                    place_id=pid,
                    lat=location.get("latitude") or geo.get("lat"),
                    lng=location.get("longitude") or geo.get("lng"),
                    url_source=source_url,
                    time_hint=time_hint,
                    added_by=added_by,
                )
                db.add(item)
                results.append(item)
            else:
                item = IdeaBinItem(
                    trip_id=trip_id,
                    title=clean_line,
                    url_source=source_url,
                    time_hint=time_hint,
                    added_by=added_by,
                )
                db.add(item)
                results.append(item)
        
        await db.commit()
        for item in results:
            await db.refresh(item)
        return results

idea_bin_service = IdeaBinService()
