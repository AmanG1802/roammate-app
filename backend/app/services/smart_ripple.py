"""Travel-time-aware ripple engine.

Only the first affected event (anchor) is shifted by delta_minutes.
Subsequent events are evaluated using the Directions API to compute actual
travel durations. An event is shifted only when the gap between the previous
event's end time and its start time is smaller than the required travel time.
If an event has sufficient buffer, propagation stops.

Events now store (day_date, start_time, end_time) as (DATE, TIME, TIME) in
trip-local wall-clock. For comparisons and shifts we combine to a UTC instant
via the trip's timezone, do the math, then split back. Shifts that would push
an event past midnight in trip-local terms are rejected (v1 disallows
overnight events — see docs/[27]).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import TimelineItem as Event, Trip
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.utils.tz import combine_in_tz, ensure_utc, split_in_tz, utc_now

log = logging.getLogger(__name__)


class CrossMidnightShiftError(Exception):
    """Raised when a ripple shift would push an event to a different day_date
    in the trip's local timezone. v1 disallows overnight; surface to the
    endpoint so it can return a structured 422."""

    def __init__(self, event_id: int, original_day, new_day):
        super().__init__(
            f"Shift would move event {event_id} from {original_day} to {new_day}; "
            "overnight shifts are not supported in v1."
        )
        self.event_id = event_id
        self.original_day = original_day
        self.new_day = new_day


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

        trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalars().first()
        trip_tz = (trip.timezone if trip else None) or "UTC"

        stmt = (
            select(Event)
            .where(
                and_(
                    Event.trip_id == trip_id,
                    Event.start_time.is_not(None),
                    Event.day_date.is_not(None),
                    Event.is_locked == False,
                    Event.is_skipped == False,
                )
            )
            .order_by(Event.day_date, Event.start_time)
        )
        result = await db.execute(stmt)
        all_events = list(result.scalars().all())

        if not all_events:
            return []

        # Precompute UTC instants for ordering and comparisons.
        starts_utc = {
            e.id: combine_in_tz(e.day_date, e.start_time, trip_tz)
            for e in all_events
        }
        ends_utc = {
            e.id: combine_in_tz(e.day_date, e.end_time, trip_tz)
            for e in all_events
        }

        if start_from_event_id is not None:
            anchor_idx = next(
                (i for i, e in enumerate(all_events) if e.id == start_from_event_id),
                None,
            )
            if anchor_idx is None:
                return []
        else:
            anchor_idx = next(
                (i for i, e in enumerate(all_events) if starts_utc[e.id] >= start_from_time),
                None,
            )
            if anchor_idx is None:
                return []

        delta = timedelta(minutes=delta_minutes)
        shifted: list[Event] = []

        anchor = all_events[anchor_idx]
        self._apply_shift(anchor, delta, trip_tz)
        starts_utc[anchor.id] = combine_in_tz(anchor.day_date, anchor.start_time, trip_tz)
        ends_utc[anchor.id] = combine_in_tz(anchor.day_date, anchor.end_time, trip_tz)
        shifted.append(anchor)

        maps_service = get_google_maps_service()

        for i in range(anchor_idx + 1, len(all_events)):
            prev = all_events[i - 1]
            curr = all_events[i]

            travel_minutes = await self._get_travel_minutes(
                prev, curr, maps_service, user_id=user_id, trip_id=trip_id
            )

            prev_end = ends_utc[prev.id] or starts_utc[prev.id]
            curr_start = starts_utc[curr.id]
            if prev_end is None or curr_start is None:
                break

            needed_gap = timedelta(minutes=travel_minutes)
            available_gap = curr_start - prev_end

            if available_gap >= needed_gap:
                break

            shortfall = needed_gap - available_gap
            self._apply_shift(curr, shortfall, trip_tz)
            starts_utc[curr.id] = combine_in_tz(curr.day_date, curr.start_time, trip_tz)
            ends_utc[curr.id] = combine_in_tz(curr.day_date, curr.end_time, trip_tz)
            shifted.append(curr)

        await db.commit()
        return shifted

    @staticmethod
    def _apply_shift(event: Event, delta: timedelta, trip_tz: str) -> None:
        """Add ``delta`` to an event's start/end in the trip's local tz.

        Rejects the shift if the new day_date would differ — v1 has no
        overnight events.
        """
        original_day = event.day_date
        start_instant = combine_in_tz(event.day_date, event.start_time, trip_tz)
        if start_instant is None:
            return
        new_start_instant = start_instant + delta
        new_day, new_start = split_in_tz(new_start_instant, trip_tz)
        if new_day != original_day:
            raise CrossMidnightShiftError(event.id, original_day, new_day)
        event.start_time = new_start

        if event.end_time is not None:
            end_instant = combine_in_tz(event.day_date, event.end_time, trip_tz)
            if end_instant is None:
                return
            new_end_instant = end_instant + delta
            new_end_day, new_end = split_in_tz(new_end_instant, trip_tz)
            if new_end_day != original_day:
                raise CrossMidnightShiftError(event.id, original_day, new_end_day)
            event.end_time = new_end

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
