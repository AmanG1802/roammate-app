"""Deterministic mock implementation of the map service.

Used when ``GOOGLE_MAPS_MOCK=true`` (the dev/CI default) or as a defensive
fallback when the real key is missing.  The mock returns the *full* shape
a real enrichment pipeline would produce so downstream code paths exercise
the same branches as production.

A small ``await asyncio.sleep`` simulates network latency so the UI's
loading states are visible during local development.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Optional

import httpx

from app.services.google_maps.base import (
    BaseMapService,
    RoutePoint,
    encode_polyline,
)


_MOCK_NETWORK_DELAY_S = 0.05


def _slug(text: str) -> str:
    return text.strip().lower().replace(" ", "_")[:48] or "unknown"


def _stable_offset(text: str) -> tuple[float, float]:
    """Derive a small repeatable lat/lng nudge from the title string."""
    digest = hashlib.md5(text.encode("utf-8")).digest()
    lat_offset = (digest[0] - 128) / 5000.0   # +/-~0.025
    lng_offset = (digest[1] - 128) / 5000.0
    return lat_offset, lng_offset


class MockMapService(BaseMapService):
    """In-memory stand-in for the real service.

    Extends ``BaseMapService`` so the enrichment loop, cache, breaker, and
    tracker are inherited.  Every external-call hook is overridden to
    return deterministic data without HTTP traffic.
    """

    _ANCHOR_LAT = 13.7563
    _ANCHOR_LNG = 100.5018

    def __init__(self) -> None:
        super().__init__(api_key=None, _mock=True)

    async def find_place(
        self,
        query: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        del client
        await asyncio.sleep(_MOCK_NETWORK_DELAY_S)
        d_lat, d_lng = _stable_offset(query)
        return {
            "id": f"mock_id_{_slug(query)}",
            "displayName": {
                "text": query.strip().title() or "Mock Place",
                "languageCode": "en",
            },
            "location": {
                "latitude": self._ANCHOR_LAT + d_lat,
                "longitude": self._ANCHOR_LNG + d_lng,
            },
            "formattedAddress": f"{query.title()}, Mock City",
            "types": ["point_of_interest", "establishment"],
        }

    async def place_details(
        self,
        place_id: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        del client
        await asyncio.sleep(_MOCK_NETWORK_DELAY_S)
        title = place_id.replace("mock_id_", "").replace("_", " ").title() or "Mock Place"
        d_lat, d_lng = _stable_offset(title)
        return {
            "id": place_id,
            "displayName": {"text": title, "languageCode": "en"},
            "location": {
                "latitude": self._ANCHOR_LAT + d_lat,
                "longitude": self._ANCHOR_LNG + d_lng,
            },
            "formattedAddress": f"{title}, Mock City",
            "rating": 4.4,
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "photos": [
                {
                    "name": f"places/{place_id}/photos/photoref_{place_id}",
                    "widthPx": 1024,
                    "heightPx": 768,
                }
            ],
            "types": ["point_of_interest", "establishment"],
        }

    def photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        seed = hashlib.md5(photo_reference.encode("utf-8")).hexdigest()[:8]
        return f"https://picsum.photos/seed/{seed}/{max_width}/600"

    def _apply_details(self, item: dict[str, Any], details: dict[str, Any]) -> None:
        """Mock uses the v2 shape internally but the base ``enrich_item``
        calls this, so we translate to normalised keys here."""
        item["place_id"] = details.get("id")

        location = details.get("location") or {}
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat is not None:
            item["lat"] = lat
        if lng is not None:
            item["lng"] = lng

        address = details.get("formattedAddress")
        if address:
            item["address"] = address

        rating = details.get("rating")
        if rating is not None:
            item["rating"] = rating

        price_enum = details.get("priceLevel")
        if isinstance(price_enum, str):
            from app.services.google_maps.v2 import _PRICE_LEVEL_ENUM_TO_INT
            mapped = _PRICE_LEVEL_ENUM_TO_INT.get(price_enum)
            if mapped is not None:
                item["price_level"] = mapped

        photos = details.get("photos") or []
        if photos and photos[0].get("name"):
            item["photo_url"] = self.photo_url(photos[0]["name"])

        gtypes = details.get("types") or []
        if gtypes and not item.get("types"):
            item["types"] = gtypes[:5]

    def _extract_place_id(self, candidate: dict[str, Any]) -> Optional[str]:
        return candidate.get("id")

    def _apply_find_place_fallback(
        self, item: dict[str, Any], candidate: dict[str, Any], pid: str
    ) -> None:
        item["place_id"] = pid
        location = candidate.get("location") or {}
        if location.get("latitude") is not None:
            item["lat"] = location["latitude"]
        if location.get("longitude") is not None:
            item["lng"] = location["longitude"]
        if candidate.get("formattedAddress"):
            item["address"] = candidate["formattedAddress"]

    async def _directions_api_call(
        self,
        waypoints: list[RoutePoint],
    ) -> dict[str, Any]:
        await asyncio.sleep(_MOCK_NETWORK_DELAY_S)
        coords: list[tuple[float, float]] = []
        legs_data: list[dict[str, Any]] = []
        for i, wp in enumerate(waypoints):
            lat = wp.lat if wp.lat is not None else self._ANCHOR_LAT
            lng = wp.lng if wp.lng is not None else self._ANCHOR_LNG
            coords.append((lat, lng))
            if i > 0:
                prev = coords[i - 1]
                for step in range(1, 5):
                    t = step / 5.0
                    coords.append((
                        prev[0] + (lat - prev[0]) * t,
                        prev[1] + (lng - prev[1]) * t,
                    ))
                dist_m = int(
                    abs(lat - prev[0]) * 111_000 + abs(lng - prev[1]) * 95_000
                ) or 500
                duration_s = max(60, dist_m // 10)
                legs_data.append(
                    {"distance_m": dist_m, "duration_s": duration_s}
                )

        encoded = encode_polyline(coords)
        return {
            "encoded_polyline": encoded,
            "legs": legs_data,
            "total_duration_s": sum(leg["duration_s"] for leg in legs_data),
            "total_distance_m": sum(leg["distance_m"] for leg in legs_data),
        }


# Backwards-compatible alias used by existing callers.
MockGoogleMapsService = MockMapService
