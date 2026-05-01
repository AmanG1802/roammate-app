"""Abstract base class for all Google Maps service implementations.

Owns the shared plumbing that every concrete backend (V1 legacy, V2 new,
mock) relies on:

  * Dataclasses: ``RoutePoint``, ``RouteLegResult``, ``RouteResult``
  * Polyline encoding utility
  * HTTP retry with exponential backoff
  * ``enrich_item`` / ``enrich_items`` (calls abstract ``find_place`` /
    ``place_details`` / ``_apply_details`` polymorphically)
  * ``directions`` wrapper (cache + breaker + tracker, delegates to
    abstract ``_directions_api_call``)

Concrete subclasses (``MapServiceV1``, ``MapServiceV2``) implement the
actual HTTP calls and response parsing for their respective API versions.
``MockMapService`` overrides the same hooks to skip the network entirely.
"""
from __future__ import annotations

import abc
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.breaker import breaker
from app.services.google_maps.tracker import track_call

log = logging.getLogger(__name__)

# ── Tunables ───────────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT_S = 10.0
ENRICH_CONCURRENCY = 5


# ── Shared dataclasses ─────────────────────────────────────────────────────

@dataclass
class RoutePoint:
    """One waypoint for the Directions / Routes request."""

    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    title: str = ""
    event_id: Optional[str] = None

    def identifier(self) -> str:
        """Stable key for the cache and API request."""
        if self.place_id:
            return f"place_id:{self.place_id}"
        if self.lat is not None and self.lng is not None:
            return f"{self.lat:.5f},{self.lng:.5f}"
        return "invalid"

    def is_valid(self) -> bool:
        return self.place_id is not None or (
            self.lat is not None and self.lng is not None
        )


@dataclass
class RouteLegResult:
    from_idx: int
    to_idx: int
    distance_m: int
    duration_s: int


@dataclass
class RouteResult:
    encoded_polyline: str
    legs: list[RouteLegResult] = field(default_factory=list)
    total_distance_m: int = 0
    total_duration_s: int = 0


# ── Polyline encoding (Google Maps polyline algorithm) ─────────────────────

def encode_polyline(coords: list[tuple[float, float]]) -> str:
    """Encode lat/lng pairs using Google's polyline algorithm."""

    def _encode(value: int) -> str:
        value = ~(value << 1) if value < 0 else (value << 1)
        chunks: list[str] = []
        while value >= 0x20:
            chunks.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        chunks.append(chr(value + 63))
        return "".join(chunks)

    result: list[str] = []
    prev_lat = 0
    prev_lng = 0
    for lat, lng in coords:
        ilat = int(round(lat * 1e5))
        ilng = int(round(lng * 1e5))
        result.append(_encode(ilat - prev_lat))
        result.append(_encode(ilng - prev_lng))
        prev_lat = ilat
        prev_lng = ilng
    return "".join(result)


def route_from_dict(data: dict[str, Any]) -> RouteResult:
    """Deserialise the normalised dict produced by ``_directions_api_call``."""
    legs = data.get("legs") or []
    return RouteResult(
        encoded_polyline=data.get("encoded_polyline", ""),
        legs=[
            RouteLegResult(
                from_idx=i,
                to_idx=i + 1,
                distance_m=int(leg.get("distance_m", 0)),
                duration_s=int(leg.get("duration_s", 0)),
            )
            for i, leg in enumerate(legs)
        ],
        total_distance_m=int(data.get("total_distance_m", 0)),
        total_duration_s=int(data.get("total_duration_s", 0)),
    )


# ── Abstract service ──────────────────────────────────────────────────────

class BaseMapService(abc.ABC):
    """Version-agnostic Google Maps service.

    Subclasses implement the four abstract hooks.  Everything else --
    caching, retry, circuit breaker, tracker, batch enrichment -- is
    handled here once.
    """

    def __init__(self, api_key: Optional[str], *, _mock: bool = False) -> None:
        self.api_key = api_key
        self._is_mock = _mock
        self._current_user_id: Optional[int] = None
        self._current_trip_id: Optional[int] = None

    def _track(self, **kwargs: Any) -> None:
        """Wrapper around track_call that injects current user/trip context."""
        kwargs.setdefault("user_id", self._current_user_id)
        kwargs.setdefault("trip_id", self._current_trip_id)
        track_call(**kwargs)

    # ── HTTP plumbing ────────────────────────────────────────────────────

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        method: str = "GET",
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        op: str,
    ) -> tuple[Optional[dict[str, Any]], int, int]:
        """Send an HTTP request with retries.

        Returns ``(json_body, attempts, http_status)``.
        """
        last_status = 0
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT_S,
                )
                last_status = resp.status_code
                if resp.status_code in RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp.json(), attempt, last_status
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= MAX_RETRIES:
                    break
                await asyncio.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
            except Exception as exc:
                last_error = exc
                break
        if last_error is not None:
            raise last_error
        return None, MAX_RETRIES, last_status

    # ── Abstract hooks (implemented per-version) ─────────────────────────

    @abc.abstractmethod
    async def find_place(
        self,
        query: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        """Find a place by free-text query.  Returns raw API-shaped dict."""
        ...

    @abc.abstractmethod
    async def place_details(
        self,
        place_id: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[dict[str, Any]]:
        """Fetch detailed place information by ``place_id``."""
        ...

    @abc.abstractmethod
    def photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        """Build a URL for a place photo."""
        ...

    @abc.abstractmethod
    def _apply_details(self, item: dict[str, Any], details: dict[str, Any]) -> None:
        """Merge API-specific detail fields into a normalised item dict.

        After this method returns the item dict must contain the
        canonical keys: ``place_id``, ``lat``, ``lng``, ``address``,
        ``rating``, ``price_level``, ``photo_url``, ``types``.
        """
        ...

    @abc.abstractmethod
    def _extract_place_id(self, candidate: dict[str, Any]) -> Optional[str]:
        """Pull the place identifier from a ``find_place`` result."""
        ...

    @abc.abstractmethod
    def _apply_find_place_fallback(
        self, item: dict[str, Any], candidate: dict[str, Any], pid: str
    ) -> None:
        """Populate ``item`` from the leaner ``find_place`` result when
        ``place_details`` fails.
        """
        ...

    @abc.abstractmethod
    async def _directions_api_call(
        self,
        waypoints: list[RoutePoint],
    ) -> dict[str, Any]:
        """Hit the backend-specific directions endpoint and normalise.

        Must return ``{"encoded_polyline", "legs", "total_distance_m",
        "total_duration_s"}``.
        """
        ...

    # ── Enrichment (shared) ──────────────────────────────────────────────

    async def enrich_item(
        self,
        item: dict[str, Any],
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        """Idempotent: items that already carry a ``place_id`` are returned as-is."""
        if item.get("place_id"):
            return item
        title = item.get("title", "")
        if not title:
            return item
        try:
            candidate = await self.find_place(title, client=client)
            if not candidate:
                return item
            pid = self._extract_place_id(candidate)
            if not pid:
                return item
            details = await self.place_details(pid, client=client)
            if details:
                self._apply_details(item, details)
            else:
                self._apply_find_place_fallback(item, candidate, pid)
        except Exception:
            log.warning("enrich_item failed for %r", title, exc_info=True)
        return item

    async def enrich_items(
        self,
        items: list[dict[str, Any]],
        *,
        user_id: Optional[int] = None,
        trip_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Parallel hydration with bounded concurrency."""
        if not items:
            return items
        if not self._is_mock and not self.api_key:
            track_call(op="enrich_batch", status="no_api_key", batch_size=len(items), user_id=user_id, trip_id=trip_id)
            return items

        self._current_user_id = user_id
        self._current_trip_id = trip_id
        sem = asyncio.Semaphore(ENRICH_CONCURRENCY)
        t0 = time.monotonic()

        async with httpx.AsyncClient() as http_client:

            async def _runner(it: dict[str, Any]) -> dict[str, Any]:
                async with sem:
                    return await self.enrich_item(it, client=http_client)

            results = await asyncio.gather(
                *[_runner(it) for it in items], return_exceptions=False
            )
        enriched = sum(1 for r in results if r.get("place_id"))
        track_call(
            op="enrich_batch",
            status="ok",
            latency_ms=int((time.monotonic() - t0) * 1000),
            batch_size=len(items),
            enriched_count=enriched,
            skipped_count=len(items) - enriched,
            breaker_state=breaker.state,
            user_id=user_id,
            trip_id=trip_id,
        )
        self._current_user_id = None
        self._current_trip_id = None
        return list(results)

    # ── Directions (shared cache + breaker + tracker) ────────────────────

    async def directions(
        self,
        waypoints: list[RoutePoint],
        *,
        user_id: Optional[int] = None,
        trip_id: Optional[int] = None,
    ) -> Optional[RouteResult]:
        """Compute a driving route through the given waypoints."""
        if len(waypoints) < 2:
            return None
        if any(not w.is_valid() for w in waypoints):
            log.warning("directions called with invalid waypoint; aborting")
            return None

        idents = [w.identifier() for w in waypoints]
        _CACHE_MODE = "driving"
        cached, state = await gmap_cache.get_directions(idents, _CACHE_MODE)
        if cached is not gmap_cache.MISS:
            track_call(
                op="directions",
                status="cache_hit" if state == "hit" else "cache_negative",
                latency_ms=0,
                cache_state=state,
                waypoint_count=len(waypoints),
                user_id=user_id,
                trip_id=trip_id,
            )
            return route_from_dict(cached) if cached else None

        if not await breaker.allow():
            track_call(
                op="directions",
                status="circuit_open",
                breaker_state="open",
                waypoint_count=len(waypoints),
                user_id=user_id,
                trip_id=trip_id,
            )
            return None

        t0 = time.monotonic()
        try:
            data = await self._directions_api_call(waypoints)
        except Exception as exc:
            await breaker.record_failure()
            track_call(
                op="directions",
                status="error",
                latency_ms=int((time.monotonic() - t0) * 1000),
                error_class=exc.__class__.__name__,
                waypoint_count=len(waypoints),
                breaker_state=breaker.state,
                user_id=user_id,
                trip_id=trip_id,
            )
            return None

        await breaker.record_success()
        await gmap_cache.set_directions(idents, _CACHE_MODE, data)
        latency_ms = int((time.monotonic() - t0) * 1000)
        track_call(
            op="directions",
            status="ok",
            latency_ms=latency_ms,
            waypoint_count=len(waypoints),
            total_distance_m=data.get("total_distance_m"),
            total_duration_s=data.get("total_duration_s"),
            cache_state="miss",
            user_id=user_id,
            trip_id=trip_id,
        )
        return route_from_dict(data)
