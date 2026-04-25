"""Google Places enrichment — called only at commit time, NOT during chat.

Hydrates BrainstormBinItem dicts with place_id, lat, lng, address,
photo_url, rating, opening_hours, phone, and website via the Google
Places API.  Items that already have a place_id are skipped.

When GOOGLE_MAPS_API_KEY is not set, the enricher is a no-op so
development / CI continues without an API key.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

_FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

_FIND_FIELDS = "place_id,name,geometry,formatted_address"
_DETAIL_FIELDS = (
    "place_id,name,geometry,formatted_address,rating,"
    "price_level,opening_hours,formatted_phone_number,"
    "website,photos,types"
)

_PHOTO_BASE = "https://maps.googleapis.com/maps/api/place/photo"


def _photo_url(photo_reference: str, max_width: int = 800) -> str:
    return (
        f"{_PHOTO_BASE}?maxwidth={max_width}"
        f"&photo_reference={photo_reference}"
        f"&key={settings.GOOGLE_MAPS_API_KEY}"
    )


async def _find_place(client: httpx.AsyncClient, query: str) -> Optional[dict[str, Any]]:
    """Call findPlaceFromText; return the top candidate or None."""
    resp = await client.get(
        _FIND_PLACE_URL,
        params={
            "input": query,
            "inputtype": "textquery",
            "fields": _FIND_FIELDS,
            "key": settings.GOOGLE_MAPS_API_KEY,
        },
        timeout=10.0,
    )
    data = resp.json()
    if data.get("status") == "OK" and data.get("candidates"):
        return data["candidates"][0]
    return None


async def _get_details(client: httpx.AsyncClient, place_id: str) -> Optional[dict[str, Any]]:
    """Call Place Details for richer fields (hours, phone, website, photo)."""
    resp = await client.get(
        _PLACE_DETAILS_URL,
        params={
            "place_id": place_id,
            "fields": _DETAIL_FIELDS,
            "key": settings.GOOGLE_MAPS_API_KEY,
        },
        timeout=10.0,
    )
    data = resp.json()
    if data.get("status") == "OK":
        return data.get("result")
    return None


def _apply_details(item: dict[str, Any], details: dict[str, Any]) -> None:
    """Merge Google Places details into a BrainstormBinItem dict in-place."""
    item["place_id"] = details.get("place_id")
    geo = details.get("geometry", {}).get("location", {})
    item["lat"] = geo.get("lat")
    item["lng"] = geo.get("lng")
    item["address"] = details.get("formatted_address")
    item["rating"] = details.get("rating")

    price = details.get("price_level")
    if price is not None:
        item["price_level"] = price

    hours = details.get("opening_hours")
    if hours and "weekday_text" in hours:
        item["opening_hours"] = {"weekday_text": hours["weekday_text"]}

    item["phone"] = details.get("formatted_phone_number")
    item["website"] = details.get("website")

    photos = details.get("photos", [])
    if photos:
        item["photo_url"] = _photo_url(photos[0]["photo_reference"])

    gtypes = details.get("types", [])
    if gtypes and not item.get("types"):
        item["types"] = gtypes[:5]


async def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich a list of BrainstormBinItem-compatible dicts with Google Places data.

    Skips items that already carry a ``place_id``.  When no API key is
    configured, returns items unchanged.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        log.debug("GOOGLE_MAPS_API_KEY not set — skipping place enrichment")
        return items

    async with httpx.AsyncClient() as client:
        for item in items:
            if item.get("place_id"):
                continue
            title = item.get("title", "")
            if not title:
                continue
            try:
                candidate = await _find_place(client, title)
                if not candidate:
                    continue
                pid = candidate.get("place_id")
                if not pid:
                    continue
                details = await _get_details(client, pid)
                if details:
                    _apply_details(item, details)
                else:
                    item["place_id"] = pid
                    geo = candidate.get("geometry", {}).get("location", {})
                    item["lat"] = geo.get("lat")
                    item["lng"] = geo.get("lng")
                    item["address"] = candidate.get("formatted_address")
            except Exception:
                log.warning("Place enrichment failed for %r", title, exc_info=True)
                continue

    return items


async def enrich_single(item_dict: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for enriching a single item."""
    result = await enrich_items([item_dict])
    return result[0]
