"""Structured logging for Google Maps API usage.

Mirrors the design of ``app.services.llm.token_tracker``: one flat
``key=value`` log line per Google call so downstream tooling (Datadog,
Loki, CloudWatch Insights) can slice without parsing nested JSON.

Events tracked:
  - find_place / place_details / photo_url / directions / enrich_batch
  - cache hits and misses
  - circuit-breaker state transitions
  - mock fallback usage

Future (out of scope for this phase): mirror counters into Redis for
daily budget caps and per-trip cost attribution.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Optional

log = logging.getLogger("roammate.google_maps")


def _hash_query(query: Optional[str]) -> Optional[str]:
    """Short, privacy-friendly hash so dashboards can join on duplicates."""
    if not query:
        return None
    return hashlib.sha1(query.strip().casefold().encode("utf-8")).hexdigest()[:10]


async def _persist_maps_usage(record: dict[str, Any]) -> None:
    """Fire-and-forget DB write — failures are logged, never raised."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.all_models import GoogleMapsApiUsage
        from app.services.admin_costs import compute_maps_cost

        cost = compute_maps_cost(record["op"], record.get("cache_state"))
        row = GoogleMapsApiUsage(
            user_id=record.get("user_id"),
            trip_id=record.get("trip_id"),
            op=record["op"],
            status=record["status"],
            latency_ms=record.get("latency_ms"),
            attempts=record.get("attempts"),
            cache_state=record.get("cache_state"),
            breaker_state=record.get("breaker_state"),
            http_status=record.get("http_status"),
            error_class=record.get("error_class"),
            batch_size=record.get("batch_size"),
            enriched_count=record.get("enriched_count"),
            cost_usd=cost,
        )
        async with AsyncSessionLocal() as session:
            session.add(row)
            await session.commit()
    except Exception:
        log.warning("_persist_maps_usage failed", exc_info=True)


def track_call(
    *,
    op: str,
    status: str,
    latency_ms: int = 0,
    attempts: int = 1,
    cache_state: Optional[str] = None,
    breaker_state: Optional[str] = None,
    query: Optional[str] = None,
    place_id: Optional[str] = None,
    http_status: Optional[int] = None,
    error_class: Optional[str] = None,
    waypoint_count: Optional[int] = None,
    total_distance_m: Optional[int] = None,
    total_duration_s: Optional[int] = None,
    batch_size: Optional[int] = None,
    enriched_count: Optional[int] = None,
    skipped_count: Optional[int] = None,
    user_id: Optional[int] = None,
    trip_id: Optional[int] = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one structured log line for a Google Maps interaction."""
    fields: dict[str, Any] = {
        "op": op,
        "status": status,
        "latency_ms": latency_ms,
        "attempts": attempts,
    }
    if cache_state is not None:
        fields["cache_state"] = cache_state
    if breaker_state is not None:
        fields["breaker_state"] = breaker_state
    qhash = _hash_query(query)
    if qhash is not None:
        fields["query_hash"] = qhash
    if place_id is not None:
        fields["place_id"] = place_id
    if http_status is not None:
        fields["http_status"] = http_status
    if error_class is not None:
        fields["error_class"] = error_class
    if waypoint_count is not None:
        fields["waypoint_count"] = waypoint_count
    if total_distance_m is not None:
        fields["total_distance_m"] = total_distance_m
    if total_duration_s is not None:
        fields["total_duration_s"] = total_duration_s
    if batch_size is not None:
        fields["batch_size"] = batch_size
    if enriched_count is not None:
        fields["enriched_count"] = enriched_count
    if skipped_count is not None:
        fields["skipped_count"] = skipped_count
    if user_id is not None:
        fields["user_id"] = user_id
    if trip_id is not None:
        fields["trip_id"] = trip_id
    if extra:
        fields.update(extra)

    log.info("google_api %s", " ".join(f"{k}={v}" for k, v in fields.items()))

    try:
        asyncio.create_task(_persist_maps_usage(fields))
    except RuntimeError:
        pass
