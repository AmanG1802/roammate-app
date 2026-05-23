"""City → centroid resolver used to seed Maps enrichment biasing.

``geocode_city`` runs the destination string ("Bengaluru, IN") through the
provider's existing ``find_place`` to get a (lat, lng). The result is cached
in ``gmap_cache`` per (city, country_code) with a 30-day TTL so common cities
cost at most one HTTP call per month per process.

This is intentionally provider-agnostic — it works against the mock, both
Google variants, and Apple Maps via the abstract ``BaseMapService`` surface.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.base import (
    BaseMapService,
    DEFAULT_BIAS_RADIUS_M,
    LocationContext,
)

log = logging.getLogger(__name__)


async def geocode_city(
    svc: BaseMapService,
    city: Optional[str],
    country_code: Optional[str],
    *,
    user_id: Optional[int] = None,
    radius_m: int = DEFAULT_BIAS_RADIUS_M,
) -> Optional[LocationContext]:
    """Resolve ``(city, country_code)`` to a ``LocationContext`` for biasing.

    Returns ``None`` when the city is missing, the lookup fails, or the
    provider returns no candidate. A country_code-only context (no centroid)
    is returned when the geocode fails but we still have a country to gate
    on — Google's ``regionCode`` alone catches most cross-country collisions.
    """
    if not city:
        return _country_only(country_code)

    cached, state = await gmap_cache.get_city_centroid(city, country_code)
    if cached is not gmap_cache.MISS:
        if cached is None:
            return _country_only(country_code)
        lat, lng = cached
        return LocationContext(
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            country_code=country_code,
        )

    # Use a country-only bias for the geocode call itself so the geocoder
    # doesn't get poisoned by a same-named city in another country.
    seed = LocationContext(country_code=country_code)
    query = f"{city}, {country_code}" if country_code else city
    svc._current_user_id = user_id  # for telemetry; cleared by the provider

    try:
        candidate = await svc.find_place(query, location=seed)
    except Exception:
        log.warning("geocode_city: find_place failed for %r", query, exc_info=True)
        candidate = None

    lat, lng = _extract_latlng(candidate)
    if lat is None or lng is None:
        await gmap_cache.set_city_centroid(city, country_code, None)
        return _country_only(country_code)

    await gmap_cache.set_city_centroid(city, country_code, (lat, lng))
    return LocationContext(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        country_code=country_code,
    )


def _country_only(country_code: Optional[str]) -> Optional[LocationContext]:
    if not country_code:
        return None
    return LocationContext(country_code=country_code)


def _extract_latlng(candidate: Optional[dict]) -> tuple[Optional[float], Optional[float]]:
    """Pull (lat, lng) from either v2/Apple shape (``location.latitude/longitude``)
    or v1 shape (``geometry.location.lat/lng``)."""
    if not candidate:
        return None, None
    loc = candidate.get("location")
    if isinstance(loc, dict):
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    geo = candidate.get("geometry")
    if isinstance(geo, dict):
        loc = geo.get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    # Apple Maps shape uses ``center: {lat, lng}``.
    center = candidate.get("center")
    if isinstance(center, dict):
        lat = center.get("lat")
        lng = center.get("lng")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    return None, None
