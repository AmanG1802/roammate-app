"""MapServiceV1 — legacy Google Maps Web Service APIs.

Uses the original ``Find Place``, ``Place Details``, ``Place Photo``, and
``Directions`` endpoints with ``key=`` query-parameter authentication.
These are cheaper for our usage profile (Find Place is $5.10/1K vs $9.60/1K
on the new Text Search SKU) and share the same free-tier caps as the new
APIs.

All shared plumbing (cache, breaker, tracker, enrichment loop) lives in
``base.py``; this file only contains the legacy-specific HTTP calls and
response parsing.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.base import BaseMapService, RoutePoint
from app.services.google_maps.breaker import breaker
from app.services.google_maps.tracker import track_call

log = logging.getLogger(__name__)

# ── Legacy endpoints ───────────────────────────────────────────────────────
_FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
_PHOTO_BASE = "https://maps.googleapis.com/maps/api/place/photo"

_FIND_FIELDS = "place_id,name,geometry,formatted_address"
_DETAIL_FIELDS_BASE = "place_id,name,geometry,formatted_address,types"


def _build_detail_fields() -> str:
    """Build the Place Details fields string based on feature flags."""
    parts = [_DETAIL_FIELDS_BASE]
    if settings.GOOGLE_MAPS_FETCH_RATING:
        parts.append("rating,price_level")
    if settings.GOOGLE_MAPS_FETCH_PHOTOS:
        parts.append("photos")
    return ",".join(parts)


class MapServiceV1(BaseMapService):
    """Google Maps service backed by the legacy Web Service APIs."""

    def __init__(self, api_key: Optional[str]) -> None:
        super().__init__(api_key=api_key)

    # ── find_place ───────────────────────────────────────────────────────

    async def find_place(
        self,
        query: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        if not query:
            return None

        cached, state = await gmap_cache.get_find_place(query)
        if cached is not gmap_cache.MISS:
            track_call(
                op="find_place",
                status="cache_hit" if state == "hit" else "cache_negative",
                latency_ms=0,
                cache_state=state,
                query=query,
            )
            return cached

        if not await breaker.allow():
            track_call(
                op="find_place",
                status="circuit_open",
                breaker_state="open",
                query=query,
            )
            return None

        t0 = time.monotonic()
        params = {
            "input": query,
            "inputtype": "textquery",
            "fields": _FIND_FIELDS,
            "key": self.api_key,
        }
        try:
            if client is not None:
                data, attempts, http_status = await self._request_with_retry(
                    client, _FIND_PLACE_URL, params=params, op="find_place",
                )
            else:
                async with httpx.AsyncClient() as own:
                    data, attempts, http_status = await self._request_with_retry(
                        own, _FIND_PLACE_URL, params=params, op="find_place",
                    )
        except Exception as exc:
            await breaker.record_failure()
            track_call(
                op="find_place",
                status="error",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
                query=query,
                breaker_state=breaker.state,
            )
            return None

        latency_ms = int((time.monotonic() - t0) * 1000)
        if data is None or data.get("status") not in {"OK", "ZERO_RESULTS"}:
            await breaker.record_failure()
            track_call(
                op="find_place",
                status="error",
                latency_ms=latency_ms,
                attempts=attempts,
                http_status=http_status,
                query=query,
                error_class=(data or {}).get("status"),
                breaker_state=breaker.state,
            )
            return None

        await breaker.record_success()
        candidates = data.get("candidates") or []
        candidate = candidates[0] if candidates else None
        await gmap_cache.set_find_place(query, candidate)
        track_call(
            op="find_place",
            status="ok" if candidate else "zero_results",
            latency_ms=latency_ms,
            attempts=attempts,
            http_status=http_status,
            cache_state="miss",
            query=query,
            place_id=(candidate or {}).get("place_id"),
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

        detail_fields = _build_detail_fields()

        cached, state = await gmap_cache.get_place_details(place_id, detail_fields)
        if cached is not gmap_cache.MISS:
            track_call(
                op="place_details",
                status="cache_hit" if state == "hit" else "cache_negative",
                latency_ms=0,
                cache_state=state,
                place_id=place_id,
            )
            return cached

        if not await breaker.allow():
            track_call(
                op="place_details",
                status="circuit_open",
                breaker_state="open",
                place_id=place_id,
            )
            return None

        t0 = time.monotonic()
        params = {
            "place_id": place_id,
            "fields": detail_fields,
            "key": self.api_key,
        }
        try:
            if client is not None:
                data, attempts, http_status = await self._request_with_retry(
                    client, _PLACE_DETAILS_URL, params=params, op="place_details",
                )
            else:
                async with httpx.AsyncClient() as own:
                    data, attempts, http_status = await self._request_with_retry(
                        own, _PLACE_DETAILS_URL, params=params, op="place_details",
                    )
        except Exception as exc:
            await breaker.record_failure()
            track_call(
                op="place_details",
                status="error",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
                place_id=place_id,
                breaker_state=breaker.state,
            )
            return None

        latency_ms = int((time.monotonic() - t0) * 1000)
        if data is None or data.get("status") != "OK":
            await breaker.record_failure()
            track_call(
                op="place_details",
                status="error",
                latency_ms=latency_ms,
                attempts=attempts,
                http_status=http_status,
                place_id=place_id,
                error_class=(data or {}).get("status"),
                breaker_state=breaker.state,
            )
            return None

        await breaker.record_success()
        result = data.get("result")
        await gmap_cache.set_place_details(place_id, detail_fields, result)
        track_call(
            op="place_details",
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
            f"{_PHOTO_BASE}?maxwidth={max_width}"
            f"&photo_reference={photo_reference}"
            f"&key={self.api_key}"
        )

    # ── _apply_details (legacy shape) ────────────────────────────────────

    def _apply_details(self, item: dict[str, Any], details: dict[str, Any]) -> None:
        item["place_id"] = details.get("place_id")
        geo = details.get("geometry", {}).get("location", {})
        item["lat"] = geo.get("lat")
        item["lng"] = geo.get("lng")
        item["address"] = details.get("formatted_address")

        if settings.GOOGLE_MAPS_FETCH_RATING:
            item["rating"] = details.get("rating")
            price = details.get("price_level")
            if price is not None:
                item["price_level"] = price

        if settings.GOOGLE_MAPS_FETCH_PHOTOS:
            photos = details.get("photos") or []
            if photos:
                ref = photos[0].get("photo_reference")
                if ref:
                    item["photo_url"] = self.photo_url(ref)

        gtypes = details.get("types") or []
        if gtypes and not item.get("types"):
            item["types"] = gtypes[:5]

    # ── find_place helpers ───────────────────────────────────────────────

    def _extract_place_id(self, candidate: dict[str, Any]) -> Optional[str]:
        return candidate.get("place_id")

    def _apply_find_place_fallback(
        self, item: dict[str, Any], candidate: dict[str, Any], pid: str
    ) -> None:
        item["place_id"] = pid
        geo = candidate.get("geometry", {}).get("location", {})
        item["lat"] = geo.get("lat")
        item["lng"] = geo.get("lng")
        item["address"] = candidate.get("formatted_address")

    # ── directions (legacy Directions API) ───────────────────────────────

    async def _directions_api_call(
        self,
        waypoints: list[RoutePoint],
    ) -> dict[str, Any]:
        def _wp_str(wp: RoutePoint) -> str:
            if wp.place_id:
                return f"place_id:{wp.place_id}"
            return f"{wp.lat},{wp.lng}"

        origin = _wp_str(waypoints[0])
        destination = _wp_str(waypoints[-1])
        params: dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "mode": "driving",
            "key": self.api_key,
        }
        if len(waypoints) > 2:
            params["waypoints"] = "|".join(_wp_str(w) for w in waypoints[1:-1])

        async with httpx.AsyncClient() as client:
            data, _attempts, http_status = await self._request_with_retry(
                client, _DIRECTIONS_URL, params=params, op="directions",
            )
        if not data or data.get("status") != "OK":
            raise RuntimeError(
                f"Directions failed: status="
                f"{data.get('status') if data else 'no_response'} "
                f"http={http_status}"
            )

        routes = data.get("routes") or []
        if not routes:
            raise RuntimeError("Directions returned no routes")
        route = routes[0]
        encoded = (route.get("overview_polyline") or {}).get("points") or ""
        legs_raw = route.get("legs") or []
        legs: list[dict[str, Any]] = []
        total_distance_m = 0
        total_duration_s = 0
        for leg in legs_raw:
            d = (leg.get("distance") or {}).get("value", 0)
            t = (leg.get("duration") or {}).get("value", 0)
            legs.append({"distance_m": int(d), "duration_s": int(t)})
            total_distance_m += int(d)
            total_duration_s += int(t)
        return {
            "encoded_polyline": encoded,
            "legs": legs,
            "total_distance_m": total_distance_m,
            "total_duration_s": total_duration_s,
        }
