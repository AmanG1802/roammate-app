"""Travel-time-aware ripple engine.

Only the first affected event (anchor) is shifted by delta_minutes.
Subsequent events are evaluated using the Directions API to compute actual
travel durations. An event is shifted only when the gap between the previous
event's end time and its start time is smaller than the required travel time.
If an event has sufficient buffer, propagation stops.

Events store (day_date, start_time, end_time) as (DATE, TIME, TIME) in
trip-local wall-clock. For comparisons and shifts we combine to a UTC instant
via the trip's timezone, do the math, then split back. Shifts that would push
an event past midnight in trip-local terms are rejected (v1 disallows
overnight events — see docs/[27]).

Transaction contract (important): the cascade NEVER commits or rolls back on
its own when an error occurs. On ``CrossMidnightShiftError`` it re-raises with
``shifted_so_far`` attached so the *caller* decides:
  - REST "running late" → rollback → 422.
  - Concierge → commit the partial shift → warn the user.
On success the non-dry path commits once. The ``dry_run`` path never commits;
it returns a ``RippleResult`` for previews and must run inside the caller's
SAVEPOINT so the in-memory mutations can be discarded.

Ripple is intentionally Concierge-only + manual REST. Raw REST CRUD
(create/update/delete events) does NOT auto-ripple — that is by design.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.all_models import DayRoute, TimelineItem as Event, Trip
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.utils.tz import combine_in_tz, ensure_utc, split_in_tz, utc_now

log = logging.getLogger(__name__)

# Per-leg Directions call budget (B2). One slow leg must not stall the request.
_DIRECTIONS_TIMEOUT_S = 4.0
# A10: transient retry schedule (seconds) before falling back to 0.
_RETRY_BACKOFF_S = (0.1, 0.2, 0.4)


class CrossMidnightShiftError(Exception):
    """Raised when a ripple shift would push an event to a different day_date
    in the trip's local timezone. v1 disallows overnight; surface to the
    caller so it can return a structured 422 (REST) or partial-commit warning
    (Concierge).

    ``shifted_so_far`` carries the events already mutated in-memory before the
    failing event, so the caller can commit them (Concierge) or roll them back
    (REST). The failing event itself is NOT mutated (``_apply_shift`` raises
    before assignment), so the list is safe to commit as-is.
    """

    def __init__(self, event_id: int, original_day, new_day, shifted_so_far=None):
        super().__init__(
            f"Shift would move event {event_id} from {original_day} to {new_day}; "
            "overnight shifts are not supported in v1."
        )
        self.event_id = event_id
        self.original_day = original_day
        self.new_day = new_day
        self.shifted_so_far: list[Event] = shifted_so_far or []


class EventNotEligibleError(Exception):
    """Raised when ``start_from_event_id`` targets an event that cannot anchor a
    shift — locked, skipped, untimed, or not on this trip. Carries a
    user-facing ``reason`` so the Concierge can explain precisely instead of
    silently reporting "nothing to shift"."""

    def __init__(self, event_id: int, reason: str, message: str):
        super().__init__(message)
        self.event_id = event_id
        self.reason = reason  # "locked" | "skipped" | "untimed" | "not_found"
        self.user_message = message


@dataclass
class ProjectedShift:
    """One event's projected before/after for dry-run previews."""

    event_id: int
    title: str
    day_date: date
    old_start: Optional[time]
    new_start: Optional[time]
    old_end: Optional[time]
    new_end: Optional[time]


@dataclass
class RippleWarning:
    kind: str  # "overlap" | "travel" | "cross_midnight" | "opening_hours"
    message: str
    event_id: Optional[int] = None


@dataclass
class RippleResult:
    """Structured cascade outcome. ``shifted`` is the list of mutated Event
    rows (for the committing path); ``projected`` + ``warnings`` drive dry-run
    previews."""

    shifted: list[Event] = field(default_factory=list)
    projected: list[ProjectedShift] = field(default_factory=list)
    warnings: list[RippleWarning] = field(default_factory=list)


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
        dry_run: bool = False,
    ):
        """Run the cascade.

        Non-dry: commits once on success and returns ``list[Event]`` (the
        shifted rows) for backward compatibility.
        Dry-run: never commits; returns the full ``RippleResult`` (projected +
        warnings) and must be called inside the caller's SAVEPOINT.
        """
        result = await self._run_cascade(
            db=db,
            trip_id=trip_id,
            delta_minutes=delta_minutes,
            start_from_time=start_from_time,
            start_from_event_id=start_from_event_id,
            user_id=user_id,
            dry_run=dry_run,
        )
        if dry_run:
            return result
        await db.commit()
        return result.shifted

    async def _run_cascade(
        self,
        db: AsyncSession,
        trip_id: int,
        delta_minutes: int,
        start_from_time=None,
        start_from_event_id: Optional[int] = None,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> RippleResult:
        result = RippleResult()

        if not start_from_time:
            start_from_time = utc_now()
        start_from_time = ensure_utc(start_from_time)

        trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalars().first()
        trip_tz = (trip.timezone if trip else None) or "UTC"
        if not trip or not trip.timezone:
            # B4: corrupt/missing tz makes the cross-midnight check use UTC
            # midnight instead of local — make it visible in observability.
            log.warning(
                "Trip %s has no/invalid timezone; falling back to UTC for ripple math",
                trip_id,
            )

        # A9: load ALL timed, non-skipped events (locked included) so locked
        # venues act as read-only waypoints rather than vanishing from routing.
        stmt = (
            select(Event)
            .where(
                and_(
                    Event.trip_id == trip_id,
                    Event.start_time.is_not(None),
                    Event.day_date.is_not(None),
                    Event.is_skipped == False,
                )
            )
            .order_by(Event.day_date, Event.start_time)
        )
        all_events = list((await db.execute(stmt)).scalars().all())

        starts_utc = {
            e.id: combine_in_tz(e.day_date, e.start_time, trip_tz) for e in all_events
        }
        ends_utc = {
            e.id: combine_in_tz(e.day_date, e.end_time, trip_tz) for e in all_events
        }

        # May raise EventNotEligibleError (A4); None means nothing to do.
        anchor_idx = await self._resolve_anchor(
            db, all_events, starts_utc, start_from_time, start_from_event_id, trip_id,
        )
        if anchor_idx is None:
            return result

        delta = timedelta(minutes=delta_minutes)
        anchor = all_events[anchor_idx]

        # B2: seed the per-call travel memo from the stored DayRoute legs for the
        # anchor's day. Driving durations depend only on the venues, not on event
        # times, so stored legs stay valid across a shift and let us skip most
        # Directions calls. New/unmatched legs fall through to a live call (which
        # then caches into the same memo to avoid recompute within this cascade).
        travel_memo: dict[tuple[int, int], float] = await self._load_leg_memo(
            db, trip_id, anchor.day_date,
        )

        # Apply the delta to the anchor (anchor is guaranteed shiftable).
        old_start, old_end = anchor.start_time, anchor.end_time
        try:
            self._apply_shift(anchor, delta, trip_tz)
        except CrossMidnightShiftError as exc:
            return self._handle_cross_midnight(exc, result, dry_run)
        starts_utc[anchor.id] = combine_in_tz(anchor.day_date, anchor.start_time, trip_tz)
        ends_utc[anchor.id] = combine_in_tz(anchor.day_date, anchor.end_time, trip_tz)
        self._record_shift(result, anchor, old_start, old_end)

        maps_service = get_google_maps_service()

        for i in range(anchor_idx + 1, len(all_events)):
            prev = all_events[i - 1]
            curr = all_events[i]

            # B1: same-day scoping — cascade never crosses midnight in v1.
            if curr.day_date != anchor.day_date:
                break

            travel_minutes = await self._get_travel_minutes(
                prev, curr, maps_service, user_id=user_id, trip_id=trip_id,
                memo=travel_memo,
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

            if curr.is_locked:
                # A9: locked events are read-only waypoints. We cannot move them,
                # so the conflict cannot be absorbed here — warn and continue so
                # downstream events are still measured from this fixed venue.
                result.warnings.append(RippleWarning(
                    kind="travel",
                    message=(
                        f"{curr.title} is locked but needs ~{int(travel_minutes)} min "
                        f"of travel and only has {int(available_gap.total_seconds() // 60)} min — "
                        "it may overlap the previous stop."
                    ),
                    event_id=curr.id,
                ))
                continue

            c_old_start, c_old_end = curr.start_time, curr.end_time
            try:
                self._apply_shift(curr, shortfall, trip_tz)
            except CrossMidnightShiftError as exc:
                return self._handle_cross_midnight(exc, result, dry_run)
            starts_utc[curr.id] = combine_in_tz(curr.day_date, curr.start_time, trip_tz)
            ends_utc[curr.id] = combine_in_tz(curr.day_date, curr.end_time, trip_tz)
            self._record_shift(result, curr, c_old_start, c_old_end)

        # R4 hook (Phase 3): opening/closing-hours warnings are appended here,
        # gated by GOOGLE_MAPS_FETCH_OPENING_HOURS, once the column + helper exist.
        self._append_opening_hours_warnings(result, all_events, trip_tz)

        return result

    async def _resolve_anchor(
        self, db, all_events, starts_utc, start_from_time, start_from_event_id, trip_id,
    ) -> Optional[int]:
        """Pick the cascade anchor index, or raise EventNotEligibleError (A4)."""
        if start_from_event_id is not None:
            anchor_idx = next(
                (i for i, e in enumerate(all_events) if e.id == start_from_event_id),
                None,
            )
            if anchor_idx is None:
                # Either filtered out (locked/skipped/untimed) or wrong trip —
                # look it up unfiltered to give a precise reason.
                await self._raise_ineligible(db, start_from_event_id, trip_id)
                return None
            if all_events[anchor_idx].is_locked:
                raise EventNotEligibleError(
                    start_from_event_id, "locked",
                    "That event is locked — unlock it to shift from there.",
                )
            return anchor_idx

        # Time-based anchor: first shiftable (non-locked) event at/after the time.
        return next(
            (
                i for i, e in enumerate(all_events)
                if not e.is_locked and starts_utc[e.id] is not None
                and starts_utc[e.id] >= start_from_time
            ),
            None,
        )

    async def _raise_ineligible(self, db, event_id: int, trip_id: int) -> None:
        ev = (await db.execute(
            select(Event).where(Event.id == event_id)
        )).scalars().first()
        if ev is None or ev.trip_id != trip_id:
            raise EventNotEligibleError(
                event_id, "not_found", "I couldn't find that event on this trip.",
            )
        if ev.is_skipped:
            raise EventNotEligibleError(
                event_id, "skipped",
                "That event is skipped — un-skip it before shifting from there.",
            )
        if ev.start_time is None or ev.day_date is None:
            raise EventNotEligibleError(
                event_id, "untimed",
                "That event has no time set, so there's nothing to shift from.",
            )
        # Locked is handled by the caller before this; default catch-all.
        raise EventNotEligibleError(
            event_id, "locked",
            "That event is locked — unlock it to shift from there.",
        )

    @staticmethod
    def _record_shift(result: RippleResult, event: Event, old_start, old_end) -> None:
        """Append to shifted/projected only if the event actually moved (A1:
        a delta=0 anchor whose time is unchanged must not be reported)."""
        if event.start_time == old_start and event.end_time == old_end:
            return
        result.shifted.append(event)
        result.projected.append(ProjectedShift(
            event_id=event.id,
            title=event.title,
            day_date=event.day_date,
            old_start=old_start,
            new_start=event.start_time,
            old_end=old_end,
            new_end=event.end_time,
        ))

    @staticmethod
    def _handle_cross_midnight(
        exc: CrossMidnightShiftError, result: RippleResult, dry_run: bool,
    ) -> RippleResult:
        """In dry-run, convert the cross-midnight failure into a warning and
        return the partial projection. In a real run, re-raise with the events
        shifted so far so the caller owns the commit/rollback decision (A3)."""
        if dry_run:
            result.warnings.append(RippleWarning(
                kind="cross_midnight",
                message="This shift would push a later event past midnight, so I stopped there.",
                event_id=exc.event_id,
            ))
            return result
        exc.shifted_so_far = result.shifted
        raise exc

    def _append_opening_hours_warnings(
        self, result: RippleResult, all_events: list[Event], trip_tz: str,
    ) -> None:
        """R4: warn (never block) when a shifted event's projected window falls
        outside its venue's opening hours. Gated by GOOGLE_MAPS_FETCH_OPENING_HOURS
        and only meaningful once events carry ``opening_hours`` (Phase 3)."""
        if not getattr(settings, "GOOGLE_MAPS_FETCH_OPENING_HOURS", False):
            return
        from app.utils.opening_hours import is_open_during

        moved_ids = {p.event_id for p in result.projected}
        for e in all_events:
            if e.id not in moved_ids:
                continue
            hours = getattr(e, "opening_hours", None)
            if not hours or e.start_time is None:
                continue
            ok = is_open_during(hours, e.day_date, e.start_time, e.end_time)
            if ok is False:
                result.warnings.append(RippleWarning(
                    kind="opening_hours",
                    message=f"{e.title} may now fall outside its opening hours.",
                    event_id=e.id,
                ))

    @staticmethod
    def _apply_shift(event: Event, delta: timedelta, trip_tz: str) -> None:
        """Add ``delta`` to an event's start/end in the trip's local tz.

        Rejects the shift if the new day_date would differ — v1 has no
        overnight events. Raises BEFORE mutating the event so a failed shift
        leaves the row untouched.
        """
        if delta == timedelta(0):
            return
        original_day = event.day_date
        start_instant = combine_in_tz(event.day_date, event.start_time, trip_tz)
        if start_instant is None:
            return
        new_start_instant = start_instant + delta
        new_day, new_start = split_in_tz(new_start_instant, trip_tz)
        if new_day != original_day:
            raise CrossMidnightShiftError(event.id, original_day, new_day)

        new_end = None
        if event.end_time is not None:
            end_instant = combine_in_tz(event.day_date, event.end_time, trip_tz)
            if end_instant is not None:
                new_end_instant = end_instant + delta
                new_end_day, new_end = split_in_tz(new_end_instant, trip_tz)
                if new_end_day != original_day:
                    raise CrossMidnightShiftError(event.id, original_day, new_end_day)

        # Both bounds validated — now mutate.
        event.start_time = new_start
        if new_end is not None:
            event.end_time = new_end

    @staticmethod
    async def _load_leg_memo(
        db: AsyncSession, trip_id: int, day_date,
    ) -> dict[tuple[int, int], float]:
        """Build {(from_event_id, to_event_id): minutes} from the stored
        DayRoute for this day, so the cascade can reuse driving durations
        instead of re-calling Directions (B2)."""
        if day_date is None:
            return {}
        route = (await db.execute(
            select(DayRoute).where(
                DayRoute.trip_id == trip_id,
                DayRoute.day_date == day_date.isoformat(),
            )
        )).scalars().first()
        memo: dict[tuple[int, int], float] = {}
        if not route or not route.legs:
            return memo
        for leg in route.legs:
            try:
                key = (int(leg["from_event_id"]), int(leg["to_event_id"]))
                memo[key] = float(leg["duration_s"]) / 60.0
            except (KeyError, TypeError, ValueError):
                continue
        return memo

    async def _get_travel_minutes(
        self,
        prev: Event,
        curr: Event,
        maps_service,
        user_id: Optional[int] = None,
        trip_id: Optional[int] = None,
        memo: Optional[dict[tuple[int, int], float]] = None,
    ) -> float:
        """Driving travel time in minutes between two events.

        B2: consult the per-call memo first (seeded from stored DayRoute legs);
        live calls cache back into it. A10: retry transient failures with
        exponential backoff before falling back to 0. B2: bound each call so one
        slow leg can't stall the request. ``directions()`` already layers caching
        + a circuit breaker underneath.
        """
        if memo is not None and (prev.id, curr.id) in memo:
            return memo[(prev.id, curr.id)]

        prev_point = self._event_to_route_point(prev)
        curr_point = self._event_to_route_point(curr)
        if not prev_point or not curr_point:
            return 0

        for attempt, backoff in enumerate(_RETRY_BACKOFF_S):
            try:
                route = await asyncio.wait_for(
                    maps_service.directions(
                        [prev_point, curr_point], user_id=user_id, trip_id=trip_id,
                    ),
                    timeout=_DIRECTIONS_TIMEOUT_S,
                )
                if route and route.legs:
                    minutes = route.legs[0].duration_s / 60.0
                    if memo is not None:
                        memo[(prev.id, curr.id)] = minutes
                    return minutes
                # A valid "no route" answer — don't retry, treat as 0.
                return 0
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001 - last attempt logs
                if attempt < len(_RETRY_BACKOFF_S) - 1:
                    await asyncio.sleep(backoff)
                    continue
                log.warning(
                    "Directions failed after %d attempts for leg event %s -> %s (trip %s); "
                    "falling back to 0 travel time",
                    len(_RETRY_BACKOFF_S), prev.id, curr.id, trip_id,
                    exc_info=True,
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
