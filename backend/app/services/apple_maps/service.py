"""Apple Maps Server API enrichment service.

Implements the same ``BaseMapService`` interface used by the Google backends
so it can be swapped in transparently for iOS enrichment requests.

Key differences from Google:
  - No photo_url, rating, or price_level — Apple doesn't provide these.
  - place_id uses Apple's internal ID format (not Google place IDs).
  - directions() is a no-op — iOS computes routes client-side via MKDirections.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from app.services.apple_maps.auth import AppleMapsTokenProvider
from app.services.google_maps.base import (
    BaseMapService,
    LocationContext,
    RoutePoint,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    REQUEST_TIMEOUT_S,
)

log = logging.getLogger(__name__)

_SEARCH_URL = "https://maps-api.apple.com/v1/search"
_PLACE_URL = "https://maps-api.apple.com/v1/place"


class AppleMapsService(BaseMapService):  # pragma: no cover
    """Apple Maps Server API backed enrichment service."""

    _directions_op: str = "apple_directions_noop"

    def __init__(
        self,
        team_id: str,
        key_id: str,
        private_key_path: str,
    ) -> None:
        super().__init__(api_key=None)
        self._token_provider = AppleMapsTokenProvider(
            team_id=team_id, key_id=key_id, private_key_path=private_key_path
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token_provider.token()}"}

    # ── find_place ───────────────────────────────────────────────────────

    async def find_place(
        self,
        query: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
        location: Optional[LocationContext] = None,
    ) -> Optional[dict[str, Any]]:
        """Apple's /v1/search endpoint accepts ``searchLocation`` (lat,lng) and
        ``searchRadius`` (metres) as soft biases — same shape we already use in
        ``nearby_search`` here. Apple has no direct country_code filter on this
        endpoint; the centroid+radius is the disambiguator. ``lang`` is honored
        when set.
        """
        if not query:
            return None

        headers = self._auth_headers()
        params: dict[str, Any] = {"q": query, "limit": "1"}
        if location is not None:
            if location.has_circle():
                params["searchLocation"] = f"{location.lat},{location.lng}"
                params["searchRadius"] = str(int(location.radius_m))
            if location.language_code:
                params["lang"] = location.language_code

        t0 = time.monotonic()
        try:
            if client is not None:
                resp = await client.get(
                    _SEARCH_URL, params=params, headers=headers,
                    timeout=REQUEST_TIMEOUT_S,
                )
            else:
                async with httpx.AsyncClient() as own:
                    resp = await own.get(
                        _SEARCH_URL, params=params, headers=headers,
                        timeout=REQUEST_TIMEOUT_S,
                    )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            log.warning("Apple Maps find_place failed for %r", query, exc_info=True)
            return None

        results = data.get("results") or []
        if not results:
            return None

        self._track(
            op="apple_find_place",
            status="ok",
            latency_ms=int((time.monotonic() - t0) * 1000),
            query=query,
        )
        return results[0]

    # ── place_details ────────────────────────────────────────────────────

    async def place_details(
        self,
        place_id: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        if not place_id:
            return None

        headers = self._auth_headers()
        url = f"{_PLACE_URL}/{place_id}"

        try:
            if client is not None:
                resp = await client.get(
                    url, headers=headers, timeout=REQUEST_TIMEOUT_S,
                )
            else:
                async with httpx.AsyncClient() as own:
                    resp = await own.get(
                        url, headers=headers, timeout=REQUEST_TIMEOUT_S,
                    )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            log.warning("Apple Maps place_details failed for %r", place_id, exc_info=True)
            return None

    # ── photo_url — Apple Maps has no photo API ──────────────────────────

    def photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        return ""

    # ── _apply_details ───────────────────────────────────────────────────

    def _apply_details(self, item: dict[str, Any], details: dict[str, Any]) -> None:
        item["place_id"] = details.get("id") or details.get("muid")

        center = details.get("center") or {}
        lat = center.get("lat")
        lng = center.get("lng")
        if lat is not None:
            item["lat"] = lat
        if lng is not None:
            item["lng"] = lng

        formatted = details.get("formattedAddressLines")
        if formatted and isinstance(formatted, list):
            item["address"] = ", ".join(formatted)
        elif details.get("name"):
            item["address"] = details["name"]

        categories = details.get("poiCategory") or details.get("category")
        if categories:
            if isinstance(categories, list):
                item["types"] = categories[:5]
            elif isinstance(categories, str):
                item["types"] = [categories]

    # ── find_place helpers ───────────────────────────────────────────────

    def _extract_place_id(self, candidate: dict[str, Any]) -> Optional[str]:
        return candidate.get("id") or candidate.get("muid")

    def _apply_find_place_fallback(
        self, item: dict[str, Any], candidate: dict[str, Any], pid: str
    ) -> None:
        item["place_id"] = pid
        center = candidate.get("center") or {}
        if center.get("lat") is not None:
            item["lat"] = center["lat"]
        if center.get("lng") is not None:
            item["lng"] = center["lng"]
        formatted = candidate.get("formattedAddressLines")
        if formatted and isinstance(formatted, list):
            item["address"] = ", ".join(formatted)

    # ── nearby_search ────────────────────────────────────────────────────

    async def nearby_search(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        headers = self._auth_headers()
        params = {
            "q": query,
            "limit": str(limit),
            "searchLocation": f"{lat},{lng}",
            "searchRadius": str(radius_m),
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _SEARCH_URL, params=params, headers=headers,
                    timeout=REQUEST_TIMEOUT_S,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            log.warning("Apple Maps nearby_search failed for %r", query, exc_info=True)
            return []

        results = (data.get("results") or [])[:limit]
        places: list[dict[str, Any]] = []
        for r in results:
            center = r.get("center") or {}
            formatted = r.get("formattedAddressLines") or []
            place: dict[str, Any] = {
                "place_id": r.get("id") or r.get("muid") or "",
                "title": r.get("name") or "",
                "address": ", ".join(formatted) if formatted else "",
                "lat": center.get("lat", 0),
                "lng": center.get("lng", 0),
                "types": [],
            }
            cat = r.get("poiCategory") or r.get("category")
            if isinstance(cat, list):
                place["types"] = cat[:5]
            elif isinstance(cat, str):
                place["types"] = [cat]
            places.append(place)
        return places

    # ── directions — no-op for Apple (iOS uses MKDirections) ─────────────

    async def _directions_api_call(
        self,
        waypoints: list[RoutePoint],
    ) -> dict[str, Any]:
        return {
            "encoded_polyline": "",
            "legs": [],
            "total_distance_m": 0,
            "total_duration_s": 0,
        }
