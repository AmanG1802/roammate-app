"""MapServiceV2 — Places API (New) + Routes API.

Uses the v1 REST endpoints with ``X-Goog-Api-Key`` header-based auth and
``X-Goog-FieldMask`` for cost-deterministic requests.  This is the
"future-proof" path — Google ships new features here — but the ``Find
Place`` equivalent (Text Search) is pricier ($9.60/1K vs $5.10/1K on the
legacy Find Place SKU).

All shared plumbing (cache, breaker, tracker, enrichment loop) lives in
``base.py``; this file only contains the v2-specific HTTP calls and
response parsing.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.base import BaseMapService, LocationContext, RoutePoint
from app.services.google_maps.breaker import breaker

log = logging.getLogger(__name__)

# ── External endpoints (Places API New + Routes API) ───────────────────────
_PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACES_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
_ROUTES_COMPUTE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_PHOTO_BASE = "https://places.googleapis.com/v1"

# ── Field masks ────────────────────────────────────────────────────────────
_SEARCH_TEXT_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.types"
)
_PLACE_DETAILS_FIELD_MASK_BASE = "id,displayName,formattedAddress,location,types"


def _build_details_field_mask() -> str:
    """Build the Place Details field mask based on feature flags."""
    parts = [_PLACE_DETAILS_FIELD_MASK_BASE]
    if settings.GOOGLE_MAPS_FETCH_RATING:
        parts.append("rating,priceLevel")
    if settings.GOOGLE_MAPS_FETCH_PHOTOS:
        parts.append("photos")
    return ",".join(parts)
_ROUTES_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,"
    "routes.polyline.encodedPolyline,"
    "routes.legs.duration,routes.legs.distanceMeters"
)

_PRICE_LEVEL_ENUM_TO_INT: dict[str, int] = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

_TRAVEL_MODE = "DRIVE"


class MapServiceV2(BaseMapService):
    """Google Maps service backed by the new Places API + Routes API."""

    _directions_op: str = "routes"

    def __init__(self, api_key: Optional[str]) -> None:
        super().__init__(api_key=api_key)

    # ── find_place ───────────────────────────────────────────────────────

    async def find_place(
        self,
        query: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
        location: Optional[LocationContext] = None,
    ) -> Optional[dict[str, Any]]:
        if not query:
            return None

        bias_fp = location.fingerprint() if location is not None else None
        cached, state = await gmap_cache.get_find_place(query, bias_fp)
        if cached is not gmap_cache.MISS:
            self._track(
                op="place_details_v2",
                status="cache_hit" if state == "hit" else "cache_negative",
                latency_ms=0,
                cache_state=state,
                query=query,
            )
            return cached

        if not await breaker.allow():
            self._track(
                op="place_details_v2",
                status="circuit_open",
                breaker_state="open",
                query=query,
            )
            return None

        t0 = time.monotonic()
        headers = {
            "X-Goog-Api-Key": self.api_key or "",
            "X-Goog-FieldMask": _SEARCH_TEXT_FIELD_MASK,
            "Content-Type": "application/json",
        }
        json_body: dict[str, Any] = {"textQuery": query}
        if location is not None:
            if location.has_circle():
                json_body["locationBias"] = {
                    "circle": {
                        "center": {
                            "latitude": location.lat,
                            "longitude": location.lng,
                        },
                        "radius": float(location.radius_m),
                    }
                }
            if location.country_code:
                # Places API v1 expects lowercase region codes.
                json_body["regionCode"] = location.country_code.lower()
            if location.language_code:
                json_body["languageCode"] = location.language_code
        try:
            if client is not None:
                data, attempts, http_status = await self._request_with_retry(
                    client,
                    _PLACES_SEARCH_TEXT_URL,
                    method="POST",
                    json_body=json_body,
                    headers=headers,
                    op="place_details_v2",
                )
            else:
                async with httpx.AsyncClient() as own:
                    data, attempts, http_status = await self._request_with_retry(
                        own,
                        _PLACES_SEARCH_TEXT_URL,
                        method="POST",
                        json_body=json_body,
                        headers=headers,
                        op="place_details_v2",
                    )
        except Exception as exc:
            await breaker.record_failure()
            self._track(
                op="place_details_v2",
                status="error",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
                query=query,
                breaker_state=breaker.state,
            )
            return None

        latency_ms = int((time.monotonic() - t0) * 1000)
        if data is None:
            await breaker.record_failure()
            self._track(
                op="place_details_v2",
                status="error",
                latency_ms=latency_ms,
                attempts=attempts,
                http_status=http_status,
                query=query,
                breaker_state=breaker.state,
            )
            return None

        await breaker.record_success()
        places = data.get("places") or []
        candidate = places[0] if places else None
        await gmap_cache.set_find_place(query, candidate, bias_fp)
        self._track(
            op="place_details_v2",
            status="ok" if candidate else "zero_results",
            latency_ms=latency_ms,
            attempts=attempts,
            http_status=http_status,
            cache_state="miss",
            query=query,
            place_id=(candidate or {}).get("id"),
        )
        return candidate

    # ── place_details ────────────────────────────────────────────────────

    async def place_details(
        self,
        place_id: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        if not place_id:
            return None

        field_mask = _build_details_field_mask()

        cached, state = await gmap_cache.get_place_details(
            place_id, field_mask
        )
        if cached is not gmap_cache.MISS:
            self._track(
                op="place_details_v2",
                status="cache_hit" if state == "hit" else "cache_negative",
                latency_ms=0,
                cache_state=state,
                place_id=place_id,
            )
            return cached

        if not await breaker.allow():
            self._track(
                op="place_details_v2",
                status="circuit_open",
                breaker_state="open",
                place_id=place_id,
            )
            return None

        t0 = time.monotonic()
        url = _PLACE_DETAILS_URL.format(place_id=place_id)
        headers = {
            "X-Goog-Api-Key": self.api_key or "",
            "X-Goog-FieldMask": field_mask,
        }
        try:
            if client is not None:
                data, attempts, http_status = await self._request_with_retry(
                    client,
                    url,
                    method="GET",
                    headers=headers,
                    op="place_details_v2",
                )
            else:
                async with httpx.AsyncClient() as own:
                    data, attempts, http_status = await self._request_with_retry(
                        own,
                        url,
                        method="GET",
                        headers=headers,
                        op="place_details_v2",
                    )
        except Exception as exc:
            await breaker.record_failure()
            self._track(
                op="place_details_v2",
                status="error",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
                place_id=place_id,
                breaker_state=breaker.state,
            )
            return None

        latency_ms = int((time.monotonic() - t0) * 1000)
        if data is None or not data.get("id"):
            await breaker.record_failure()
            self._track(
                op="place_details_v2",
                status="error",
                latency_ms=latency_ms,
                attempts=attempts,
                http_status=http_status,
                place_id=place_id,
                breaker_state=breaker.state,
            )
            return None

        await breaker.record_success()
        result = data
        await gmap_cache.set_place_details(
            place_id, field_mask, result
        )
        self._track(
            op="place_details_v2",
            status="ok" if result else "zero_results",
            latency_ms=latency_ms,
            attempts=attempts,
            http_status=http_status,
            cache_state="miss",
            place_id=place_id,
        )
        return result

    # ── photo_url ────────────────────────────────────────────────────────

    def photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        return (
            f"{_PHOTO_BASE}/{photo_reference}/media"
            f"?maxWidthPx={max_width}"
            f"&key={self.api_key}"
        )

    # ── _apply_details (v2 shape) ────────────────────────────────────────

    def _apply_details(self, item: dict[str, Any], details: dict[str, Any]) -> None:
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

        if settings.GOOGLE_MAPS_FETCH_RATING:
            rating = details.get("rating")
            if rating is not None:
                item["rating"] = rating
            price_enum = details.get("priceLevel")
            if isinstance(price_enum, str):
                mapped = _PRICE_LEVEL_ENUM_TO_INT.get(price_enum)
                if mapped is not None:
                    item["price_level"] = mapped

        if settings.GOOGLE_MAPS_FETCH_PHOTOS:
            photos = details.get("photos") or []
            if photos and photos[0].get("name"):
                item["photo_url"] = self.photo_url(photos[0]["name"])

        gtypes = details.get("types") or []
        if gtypes and not item.get("types"):
            item["types"] = gtypes[:5]

    # ── find_place helpers ───────────────────────────────────────────────

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

    # ── nearby_search (Text Search or Nearby Search — new APIs) ─────────

    async def nearby_search(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        field_parts = [
            "places.id", "places.displayName", "places.formattedAddress",
            "places.location", "places.types",
        ]
        if settings.GOOGLE_MAPS_FETCH_RATING:
            field_parts.extend(["places.rating", "places.priceLevel"])
        if settings.GOOGLE_MAPS_FETCH_PHOTOS:
            field_parts.append("places.photos")
        field_mask = ",".join(field_parts)

        headers = {
            "X-Goog-Api-Key": self.api_key or "",
            "X-Goog-FieldMask": field_mask,
            "Content-Type": "application/json",
        }

        circle = {
            "center": {"latitude": lat, "longitude": lng},
            "radius": float(radius_m),
        }

        if settings.GOOGLE_MAPS_USE_NEARBY_API:
            url = _PLACES_SEARCH_NEARBY_URL
            json_body: dict[str, Any] = {
                "locationRestriction": {"circle": circle},
                "maxResultCount": limit,
            }
        else:
            url = _PLACES_SEARCH_TEXT_URL
            json_body = {
                "textQuery": query,
                "locationBias": {"circle": circle},
                "maxResultCount": limit,
            }

        import time as _time
        t0 = _time.monotonic()
        try:
            async with httpx.AsyncClient() as client:
                data, attempts, http_status = await self._request_with_retry(
                    client, url, method="POST",
                    json_body=json_body, headers=headers, op="nearby_or_text_search",
                )
        except Exception as exc:
            self._track(
                op="nearby_or_text_search", status="error",
                latency_ms=int((_time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
            )
            return []

        if not data:
            return []

        results = (data.get("places") or [])[:limit]
        places: list[dict[str, Any]] = []
        for r in results:
            loc = r.get("location") or {}
            display = r.get("displayName") or {}
            place: dict[str, Any] = {
                "place_id": r.get("id", ""),
                "title": display.get("text", ""),
                "address": r.get("formattedAddress", ""),
                "lat": loc.get("latitude", 0),
                "lng": loc.get("longitude", 0),
                "types": (r.get("types") or [])[:5],
            }
            if settings.GOOGLE_MAPS_FETCH_RATING:
                place["rating"] = r.get("rating")
                price_enum = r.get("priceLevel")
                if isinstance(price_enum, str):
                    place["price_level"] = _PRICE_LEVEL_ENUM_TO_INT.get(price_enum)
                else:
                    place["price_level"] = price_enum
            if settings.GOOGLE_MAPS_FETCH_PHOTOS:
                photos = r.get("photos") or []
                if photos and photos[0].get("name"):
                    place["photo_url"] = self.photo_url(photos[0]["name"])
            places.append(place)

        self._track(
            op="nearby_or_text_search", status="ok",
            latency_ms=int((_time.monotonic() - t0) * 1000),
        )
        return places

    # ── directions (Routes API) ──────────────────────────────────────────

    async def _directions_api_call(
        self,
        waypoints: list[RoutePoint],
    ) -> dict[str, Any]:
        def _wp_obj(wp: RoutePoint) -> dict[str, Any]:
            if wp.place_id:
                return {"placeId": wp.place_id}
            return {
                "location": {
                    "latLng": {
                        "latitude": wp.lat,
                        "longitude": wp.lng,
                    }
                }
            }

        json_body: dict[str, Any] = {
            "origin": _wp_obj(waypoints[0]),
            "destination": _wp_obj(waypoints[-1]),
            "travelMode": _TRAVEL_MODE,
            "polylineEncoding": "ENCODED_POLYLINE",
        }
        if len(waypoints) > 2:
            json_body["intermediates"] = [_wp_obj(w) for w in waypoints[1:-1]]

        headers = {
            "X-Goog-Api-Key": self.api_key or "",
            "X-Goog-FieldMask": _ROUTES_FIELD_MASK,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            data, _attempts, http_status = await self._request_with_retry(
                client,
                _ROUTES_COMPUTE_URL,
                method="POST",
                json_body=json_body,
                headers=headers,
                op="routes",
            )
        if not data:
            raise RuntimeError(
                f"Routes API returned no body (http={http_status})"
            )

        routes = data.get("routes") or []
        if not routes:
            raise RuntimeError("Routes API returned no routes")
        route = routes[0]
        encoded = (route.get("polyline") or {}).get("encodedPolyline") or ""

        def _parse_duration_s(raw: Any) -> int:
            if isinstance(raw, str):
                stripped = raw.rstrip("sS").strip() or "0"
                try:
                    return int(float(stripped))
                except ValueError:
                    return 0
            if isinstance(raw, (int, float)):
                return int(raw)
            return 0

        legs_raw = route.get("legs") or []
        legs: list[dict[str, Any]] = []
        total_distance_m = 0
        total_duration_s = 0
        for leg in legs_raw:
            distance_m = int(leg.get("distanceMeters") or 0)
            duration_s = _parse_duration_s(leg.get("duration"))
            legs.append({"distance_m": distance_m, "duration_s": duration_s})
            total_distance_m += distance_m
            total_duration_s += duration_s

        if not legs_raw:
            total_distance_m = int(route.get("distanceMeters") or 0)
            total_duration_s = _parse_duration_s(route.get("duration"))

        return {
            "encoded_polyline": encoded,
            "legs": legs,
            "total_distance_m": total_distance_m,
            "total_duration_s": total_duration_s,
        }
