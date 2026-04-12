import json
from typing import List, Optional, Dict, Any
from app.core.config import settings
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class NLPService:
    async def parse_quick_add(self, text: str) -> Dict[str, Any]:
        """
        Parses a natural language string into a structured event object.
        Example: "Dinner at Gusto tomorrow at 8pm" -> {title: "Dinner at Gusto", start_time: ...}
        """
        if not settings.OPENAI_API_KEY:
            # Fallback mock for development
            return {
                "title": text,
                "start_time": None, # Should be handled by service
                "event_type": "activity"
            }

        prompt = f"""
        Extract travel event details from the following text: "{text}"
        Return a JSON object with:
        - title: The name of the place or activity
        - start_time_iso: Optional ISO format start time if mentioned
        - duration_minutes: Estimated duration in minutes (default 60)
        - event_type: One of [activity, transport, lodging, food]
        
        If the year/month/day isn't clear, focus on the time and relative day (e.g., 'tomorrow').
        JSON only:
        """

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        return json.loads(response.choices[0].message.content)

nlp_service = NLPService()
