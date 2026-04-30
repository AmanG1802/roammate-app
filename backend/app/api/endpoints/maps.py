"""Trip-route endpoint backed by ``GoogleMapsService.directions()``.

The frontend Planner / Live map exposes a refresh button that posts here
with a ``day_date``.  Travel mode is fixed to driving server-side.  We:

  1. Load the caller's events for that day.
  2. **Hard gate A — missing start times.** If any event lacks
     ``start_time`` we return ``422`` with ``detail="missing_start_times"``
     and the offending ids; no Google call is made.
  3. **Hard gate B — time conflicts.** Walking the day's events in
     ``sort_order`` ASC (matching the Timeline UI), if any consecutive
     pair satisfies ``prev.end_time > curr.start_time`` we return ``422``
     with ``detail="time_conflicts"`` and every event id involved.
  4. Order the day's events by ``(start_time ASC, sort_order ASC)``.
  5. Soft-skip events without a routable location (``no_location``).
  6. Build ``RoutePoint`` waypoints and call
     ``GoogleMapsService.directions``.

422 (Unprocessable Entity) is used for the gates because the request
itself is well-formed — it's the underlying timeline data that fails
business rules.  The frontend distinguishes by ``detail`` and renders
the matching toast.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.all_models import Event as EventModel, User
from app.schemas.route import RouteLeg, RouteResponse, UnroutableEvent
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.services.roles import require_trip_member

router = APIRouter()


class RouteRequest(BaseModel):
    day_date: date


def _has_conflict(prev: EventModel, curr: EventModel) -> bool:
    """Mirror the frontend Timeline ``hasConflict`` helper.

    A conflict exists when the previous event's ``end_time`` is strictly
    after the next event's ``start_time``.  Missing bounds → not a
    conflict (matches the UI behaviour at Timeline.tsx:22-25).
    """
    if prev.end_time is None or curr.start_time is None:
        return False
    return prev.end_time > curr.start_time


@router.post("/{trip_id}/route", response_model=RouteResponse)
async def compute_route(
    trip_id: int,
    body: RouteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RouteResponse:
    await require_trip_member(db, trip_id, current_user.id)

    stmt = select(EventModel).where(
        EventModel.trip_id == trip_id,
        EventModel.day_date == body.day_date,
    )
    events: list[EventModel] = list((await db.execute(stmt)).scalars().all())

    if not events:
        return RouteResponse(reason="need_two_points")

    # ── Gate A: missing start times ──────────────────────────────────────
    missing_ids = [str(e.id) for e in events if e.start_time is None]
    if missing_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "missing_start_times",
                "offending_event_ids": missing_ids,
            },
        )

    # ── Gate B: time conflicts (walks events in the same order the
    # Timeline UI displays them — see frontend/lib/store.ts:165-168 and
    # frontend/components/trip/Timeline.tsx:277-278).  This means every
    # conflict we 422 on corresponds to a red time icon the user can
    # see; we never block on a pair the UI hasn't already flagged. ──
    def _timeline_order_key(e: EventModel) -> tuple[int, datetime, int]:
        # Bucket 0: timed events sorted by start_time
        # Bucket 1: TBD events sorted by sort_order
        if e.start_time is not None:
            return (0, e.start_time, e.sort_order or 0)
        return (1, datetime.max, e.sort_order or 0)

    by_timeline = sorted(events, key=_timeline_order_key)
    conflict_ids: list[str] = []
    for i in range(1, len(by_timeline)):
        prev = by_timeline[i - 1]
        curr = by_timeline[i]
        if _has_conflict(prev, curr):
            # Both sides of every conflicting pair go in the response so
            # the UI can highlight them all.
            conflict_ids.append(str(prev.id))
            conflict_ids.append(str(curr.id))
    if conflict_ids:
        # De-duplicate while preserving first-seen order.
        seen = set()
        deduped: list[str] = []
        for cid in conflict_ids:
            if cid not in seen:
                seen.add(cid)
                deduped.append(cid)
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "time_conflicts",
                "offending_event_ids": deduped,
            },
        )

    # ── Route order: start_time ASC, sort_order ASC tiebreak ────────────
    ordered = sorted(
        events,
        key=lambda e: (
            e.start_time or datetime.min,
            e.sort_order or 0,
        ),
    )

    # Partition into routable / unroutable based on coordinates.
    routable: list[EventModel] = []
    unroutable_no_loc: list[UnroutableEvent] = []
    for e in ordered:
        if e.place_id or (e.lat is not None and e.lng is not None):
            routable.append(e)
        else:
            unroutable_no_loc.append(
                UnroutableEvent(event_id=str(e.id), reason="no_location")
            )

    if len(routable) < 2:
        return RouteResponse(
            ordered_event_ids=[str(e.id) for e in routable],
            unroutable=unroutable_no_loc,
            reason="need_two_points",
        )

    waypoints = [
        RoutePoint(
            place_id=e.place_id,
            lat=e.lat,
            lng=e.lng,
            title=e.title,
            event_id=str(e.id),
        )
        for e in routable
    ]
    service = get_google_maps_service()
    route = await service.directions(waypoints, user_id=current_user.id, trip_id=trip_id)
    if route is None:
        return RouteResponse(
            ordered_event_ids=[str(e.id) for e in routable],
            unroutable=unroutable_no_loc,
            reason="need_two_points",
        )

    legs = [
        RouteLeg(
            from_event_id=str(routable[leg.from_idx].id),
            to_event_id=str(routable[leg.to_idx].id),
            duration_s=leg.duration_s,
            distance_m=leg.distance_m,
        )
        for leg in route.legs
    ]

    return RouteResponse(
        encoded_polyline=route.encoded_polyline or None,
        legs=legs,
        total_duration_s=route.total_duration_s,
        total_distance_m=route.total_distance_m,
        ordered_event_ids=[str(e.id) for e in routable],
        unroutable=unroutable_no_loc,
        reason=None,
    )
