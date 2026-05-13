"""Schemas for the trip route endpoint."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class RouteLeg(BaseModel):
    from_event_id: str
    to_event_id: str
    duration_s: int
    distance_m: int


class UnroutableEvent(BaseModel):
    """An event soft-skipped from the route.

    Missing-start-time and conflicts are *hard* gates that produce a 422
    before the route is computed at all (see ``RouteValidationError``);
    only ``no_location`` events flow through ``RouteResponse.unroutable``.
    """

    event_id: str
    reason: Literal["no_location"]


class RouteResponse(BaseModel):
    encoded_polyline: Optional[str] = None
    legs: list[RouteLeg] = []
    total_duration_s: int = 0
    total_distance_m: int = 0
    # start_time-sorted event ids that made it into the route
    ordered_event_ids: list[str] = []
    unroutable: list[UnroutableEvent] = []
    # ``need_two_points`` — fewer than 2 routable events on this day.
    reason: Optional[Literal["need_two_points"]] = None
    # Persistence fields — populated when route is stored/fetched from DB
    waypoint_fingerprint: Optional[str] = None
    computed_at: Optional[datetime] = None
    is_stale: bool = False


class RouteValidationError(BaseModel):
    """Body of a 422 returned when a hard pre-flight gate fails.

    ``detail`` distinguishes the two gates so the frontend can render the
    matching toast; ``offending_event_ids`` lets the UI optionally
    highlight the offending rows in the timeline.
    """

    detail: Literal["missing_start_times", "time_conflicts"]
    offending_event_ids: list[str]
