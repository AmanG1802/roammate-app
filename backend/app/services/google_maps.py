import httpx
from typing import Optional, Dict, Any
from app.core.config import settings

class GoogleMapsService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

    async def find_place(self, text: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            # Fallback for development without API key
            return {
                "name": text,
                "place_id": f"mock_id_{text.replace(' ', '_')}",
                "geometry": {"location": {"lat": 41.8902, "lng": 12.4922}} # Defaults to Rome
            }

        params = {
            "input": text,
            "inputtype": "textquery",
            "fields": "name,place_id,geometry",
            "key": self.api_key
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            data = response.json()
            
            if data.get("status") == "OK" and data.get("candidates"):
                return data["candidates"][0]
            
            return None

google_maps_service = GoogleMapsService()
