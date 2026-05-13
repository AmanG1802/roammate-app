"""Travel-time-aware ripple engine.

Only the first affected event (anchor) is shifted by delta_minutes.
Subsequent events are evaluated using the Directions API to compute actual
travel durations. An event is shifted only when the gap between the previous
event's end time and its start time is smaller than the required travel time.
If an event has sufficient buffer, propagation stops.

All datetime comparisons use UTC-aware timestamps.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import TimelineItem as Event
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.utils.tz import utc_now, ensure_utc

log = logging.getLogger(__name__)


class SmartRippleEngine:
    """Shift itinerary events intelligently using real travel times."""

    async def shift_itinerary(
        self,
        db: AsyncSession,
        trip_id: int,
        delta_minutes: int,
        start_from_time=None,
        start_from_event_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> list[Event]:
        if not start_from_time:
            start_from_time = utc_now()
        start_from_time = ensure_utc(start_from_time)

        stmt = (
            select(Event)
            .where(
                and_(
                    Event.trip_id == trip_id,
                    Event.start_time.is_not(None),
                    Event.is_locked == False,
                    Event.is_skipped == False,
                )
            )
            .order_by(Event.start_time)
        )
        result = await db.execute(stmt)
        all_events = list(result.scalars().all())

        for e in all_events:
            e.start_time = ensure_utc(e.start_time)
            e.end_time = ensure_utc(e.end_time)

        if not all_events:
            return []

        if start_from_event_id is not None:
            anchor_idx = next(
                (i for i, e in enumerate(all_events) if e.id == start_from_event_id),
                None,
            )
            if anchor_idx is None:
                return []
        else:
            anchor_idx = next(
                (i for i, e in enumerate(all_events) if e.start_time >= start_from_time),
                None,
            )
            if anchor_idx is None:
                return []

        delta = timedelta(minutes=delta_minutes)
        shifted: list[Event] = []

        anchor = all_events[anchor_idx]
        anchor.start_time += delta
        if anchor.end_time is not None:
            anchor.end_time += delta
        shifted.append(anchor)

        maps_service = get_google_maps_service()

        for i in range(anchor_idx + 1, len(all_events)):
            prev = all_events[i - 1]
            curr = all_events[i]

            travel_minutes = await self._get_travel_minutes(
                prev, curr, maps_service, user_id=user_id, trip_id=trip_id
            )

            prev_end = prev.end_time or prev.start_time
            if prev_end is None:
                break

            needed_gap = timedelta(minutes=travel_minutes)
            available_gap = curr.start_time - prev_end

            if available_gap >= needed_gap:
                break

            shortfall = needed_gap - available_gap
            curr.start_time += shortfall
            if curr.end_time is not None:
                curr.end_time += shortfall
            shifted.append(curr)

        await db.commit()
        return shifted

    async def _get_travel_minutes(
        self,
        prev: Event,
        curr: Event,
        maps_service,
        user_id: Optional[int] = None,
        trip_id: Optional[int] = None,
    ) -> float:
        """Get driving travel time in minutes between two events."""
        prev_point = self._event_to_route_point(prev)
        curr_point = self._event_to_route_point(curr)

        if not prev_point or not curr_point:
            return 0

        try:
            route = await maps_service.directions(
                [prev_point, curr_point],
                user_id=user_id,
                trip_id=trip_id,
            )
            if route and route.legs:
                return route.legs[0].duration_s / 60.0
        except Exception:
            log.warning(
                "Directions call failed for travel between event %s and %s",
                prev.id, curr.id, exc_info=True,
            )
        return 0

    @staticmethod
    def _event_to_route_point(event: Event) -> Optional[RoutePoint]:
        if event.place_id:
            return RoutePoint(place_id=event.place_id, title=event.title)
        if event.lat is not None and event.lng is not None:
            return RoutePoint(lat=event.lat, lng=event.lng, title=event.title)
        return None


smart_ripple_engine = SmartRippleEngine()
