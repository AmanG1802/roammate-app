"""Async-safe TTL+LRU caches for Google Maps responses.

Three namespaces:
  - find_place: keyed on the normalized query string (24h TTL).
  - place_details: keyed on (place_id, fields_signature) (7d TTL).
  - directions: keyed on the ordered tuple of place_id/coord identifiers (1h TTL).

Negative results (None) are cached with a shorter TTL so we don't hammer
Google for the same garbage queries every time the user clicks refresh.

Sentinel ``MISS`` is used so that explicit ``None`` (= negative cache)
can be distinguished from "not in cache".
"""
from __future__ import annotations

import asyncio
from typing import Any, Hashable, Optional, Tuple

from cachetools import TTLCache


class _CacheMiss:
    """Sentinel marking an absent key (so None can mean negative-hit)."""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "<MISS>"


MISS: Any = _CacheMiss()

# Cache sizes are intentionally modest — Google enforces per-key cost too,
# so these mostly defend against pathological user behaviour, not memory
# pressure.  Tune if a workload demands it.
_FIND_PLACE_TTL = 24 * 60 * 60       # 24 hours
_PLACE_DETAILS_TTL = 7 * 24 * 60 * 60  # 7 days
_DIRECTIONS_TTL = 60 * 60            # 1 hour
_TIMEZONE_TTL = 30 * 24 * 60 * 60    # 30 days — timezones don't change often
_NEGATIVE_TTL = 60 * 60              # 1 hour for None results

_find_place_cache: TTLCache = TTLCache(maxsize=4096, ttl=_FIND_PLACE_TTL)
_place_details_cache: TTLCache = TTLCache(maxsize=4096, ttl=_PLACE_DETAILS_TTL)
_directions_cache: TTLCache = TTLCache(maxsize=1024, ttl=_DIRECTIONS_TTL)
_timezone_cache: TTLCache = TTLCache(maxsize=4096, ttl=_TIMEZONE_TTL)
_negative_cache: TTLCache = TTLCache(maxsize=2048, ttl=_NEGATIVE_TTL)

_lock = asyncio.Lock()


def _normalize_query(query: str) -> str:
    return query.strip().casefold()


def _find_place_key(query: str, bias_fp: Optional[str]) -> Tuple[str, Optional[str]]:
    """Build the cache key. ``bias_fp=None`` preserves the legacy key shape
    so existing un-biased entries are still hit after this change."""
    return (_normalize_query(query), bias_fp)


async def get_find_place(
    query: str, bias_fp: Optional[str] = None,
) -> Tuple[Any, str]:
    """Return ``(value, state)`` where state is ``hit|negative_hit|miss``."""
    key = _find_place_key(query, bias_fp)
    async with _lock:
        if key in _find_place_cache:
            return _find_place_cache[key], "hit"
        if ("find_place", key) in _negative_cache:
            return None, "negative_hit"
    return MISS, "miss"


async def set_find_place(
    query: str,
    value: Optional[dict[str, Any]],
    bias_fp: Optional[str] = None,
) -> None:
    key = _find_place_key(query, bias_fp)
    async with _lock:
        if value is None:
            _negative_cache[("find_place", key)] = True
        else:
            _find_place_cache[key] = value


# ── City-centroid cache (used by geocode_city to avoid re-resolving a city
#    on every plan-trip request). Keyed on (lower_city, upper_country_code).
_city_centroid_cache: TTLCache = TTLCache(maxsize=2048, ttl=_TIMEZONE_TTL)


def _city_centroid_key(city: str, country_code: Optional[str]) -> Tuple[str, str]:
    return (city.strip().casefold(), (country_code or "").strip().upper())


async def get_city_centroid(
    city: str, country_code: Optional[str],
) -> Tuple[Any, str]:
    key = _city_centroid_key(city, country_code)
    async with _lock:
        if key in _city_centroid_cache:
            return _city_centroid_cache[key], "hit"
        if ("city_centroid", key) in _negative_cache:
            return None, "negative_hit"
    return MISS, "miss"


async def set_city_centroid(
    city: str,
    country_code: Optional[str],
    value: Optional[tuple[float, float]],
) -> None:
    key = _city_centroid_key(city, country_code)
    async with _lock:
        if value is None:
            _negative_cache[("city_centroid", key)] = True
        else:
            _city_centroid_cache[key] = value


async def get_place_details(place_id: str, fields_sig: str) -> Tuple[Any, str]:
    key = (place_id, fields_sig)
    async with _lock:
        if key in _place_details_cache:
            return _place_details_cache[key], "hit"
        if ("place_details", place_id, fields_sig) in _negative_cache:
            return None, "negative_hit"
    return MISS, "miss"


async def set_place_details(
    place_id: str, fields_sig: str, value: Optional[dict[str, Any]]
) -> None:
    key = (place_id, fields_sig)
    async with _lock:
        if value is None:
            _negative_cache[("place_details", place_id, fields_sig)] = True
        else:
            _place_details_cache[key] = value


def _directions_key(waypoint_idents: list[str], mode: str) -> Hashable:
    return (mode, tuple(waypoint_idents))


async def get_directions(waypoint_idents: list[str], mode: str) -> Tuple[Any, str]:
    key = _directions_key(waypoint_idents, mode)
    async with _lock:
        if key in _directions_cache:
            return _directions_cache[key], "hit"
        if ("directions", key) in _negative_cache:
            return None, "negative_hit"
    return MISS, "miss"


async def set_directions(
    waypoint_idents: list[str], mode: str, value: Optional[dict[str, Any]]
) -> None:
    key = _directions_key(waypoint_idents, mode)
    async with _lock:
        if value is None:
            _negative_cache[("directions", key)] = True
        else:
            _directions_cache[key] = value


def _timezone_key(lat: float, lng: float) -> Tuple[float, float]:
    """Round lat/lng to a ~1km grid cell — tz boundaries are coarse enough."""
    return (round(lat, 2), round(lng, 2))


async def get_timezone(lat: float, lng: float) -> Tuple[Any, str]:
    key = _timezone_key(lat, lng)
    async with _lock:
        if key in _timezone_cache:
            return _timezone_cache[key], "hit"
        if ("timezone", key) in _negative_cache:
            return None, "negative_hit"
    return MISS, "miss"


async def set_timezone(lat: float, lng: float, value: Optional[str]) -> None:
    key = _timezone_key(lat, lng)
    async with _lock:
        if value is None:
            _negative_cache[("timezone", key)] = True
        else:
            _timezone_cache[key] = value


def clear_all() -> None:
    """Test-only utility to reset all caches between cases."""
    _find_place_cache.clear()
    _place_details_cache.clear()
    _directions_cache.clear()
    _timezone_cache.clear()
    _city_centroid_cache.clear()
    _negative_cache.clear()
