"""Apple Maps Server API service package.

Resolution order for ``get_apple_maps_service()``:

1. ``settings.APPLE_MAPS_ENABLED`` is False -> None (caller should fall back
   to Google).
2. Required credentials missing -> None (with warning log).
3. Otherwise -> AppleMapsService.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from app.core.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_apple_maps_service() -> Optional["AppleMapsService"]:
    if not settings.APPLE_MAPS_ENABLED:
        return None

    missing = []
    if not settings.APPLE_MAPS_TEAM_ID:
        missing.append("APPLE_MAPS_TEAM_ID")
    if not settings.APPLE_MAPS_KEY_ID:
        missing.append("APPLE_MAPS_KEY_ID")
    if not settings.APPLE_MAPS_PRIVATE_KEY_PATH:
        missing.append("APPLE_MAPS_PRIVATE_KEY_PATH")

    if missing:
        log.error(
            "APPLE_MAPS_ENABLED=True but missing: %s; Apple Maps unavailable",
            ", ".join(missing),
        )
        return None

    from app.services.apple_maps.service import AppleMapsService

    return AppleMapsService(
        team_id=settings.APPLE_MAPS_TEAM_ID,
        key_id=settings.APPLE_MAPS_KEY_ID,
        private_key_path=settings.APPLE_MAPS_PRIVATE_KEY_PATH,
    )


__all__ = ["get_apple_maps_service"]
