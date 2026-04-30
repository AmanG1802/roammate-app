"""Public surface of the Google Maps service package.

Resolution order for ``get_google_maps_service()``:

1. ``settings.GOOGLE_MAPS_MOCK`` is True  -> MockMapService.
2. ``settings.GOOGLE_MAPS_API_KEY`` missing -> MockMapService
   (with a loud log so prod misconfiguration is obvious).
3. ``settings.GOOGLE_MAPS_API_VERSION == "v2"`` -> MapServiceV2.
4. Otherwise (default ``"v1"``) -> MapServiceV1.

The factory is cached for the lifetime of the process so the cache and
circuit breaker singletons are shared across requests.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings
from app.services.google_maps.base import (
    BaseMapService,
    RoutePoint,
    RouteLegResult,
    RouteResult,
    encode_polyline,
)
from app.services.google_maps.mock import MockMapService

log = logging.getLogger(__name__)

# Backwards-compatible aliases so existing imports keep working.
MockGoogleMapsService = MockMapService


@lru_cache(maxsize=1)
def get_google_maps_service() -> BaseMapService:
    if settings.GOOGLE_MAPS_MOCK:
        return MockMapService()
    if not settings.GOOGLE_MAPS_API_KEY:
        log.error(
            "GOOGLE_MAPS_API_KEY missing while GOOGLE_MAPS_MOCK=False; "
            "falling back to MockMapService"
        )
        return MockMapService()
    if settings.GOOGLE_MAPS_API_VERSION == "v2":
        from app.services.google_maps.v2 import MapServiceV2
        return MapServiceV2(api_key=settings.GOOGLE_MAPS_API_KEY)
    from app.services.google_maps.v1 import MapServiceV1
    return MapServiceV1(api_key=settings.GOOGLE_MAPS_API_KEY)


__all__ = [
    "BaseMapService",
    "MockMapService",
    "MockGoogleMapsService",
    "RoutePoint",
    "RouteLegResult",
    "RouteResult",
    "encode_polyline",
    "get_google_maps_service",
]
