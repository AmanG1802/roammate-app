from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import timedelta
from typing import List, Optional
from app.models.all_models import TimelineItem as Event, Trip
from app.utils.tz import combine_in_tz, split_in_tz, utc_now


class RippleEngine:
    """Legacy ripple engine kept for the basic shift-by-delta API.

    See :class:`app.services.smart_ripple.SmartRippleEngine` for the
    travel-time-aware variant; this one just shifts every event after
    *start_from_time* by *delta_minutes*.

    Events store (day_date, start_time, end_time) as (DATE, TIME, TIME) in
    trip-local wall-clock. We combine to UTC instants for ordering /
    arithmetic and split back. Shifts that would cross midnight in
    trip-local terms are skipped (v1 disallows overnight events).
    """

    async def shift_itinerary(
        self,
        db: AsyncSession,
        trip_id: int,
        delta_minutes: int,
        start_from_time=None,
    ) -> List[Event]:
        if not start_from_time:
            start_from_time = utc_now()

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
                )
            )
            .order_by(Event.day_date, Event.start_time)
        )

        result = await db.execute(stmt)
        events = list(result.scalars().all())
        delta = timedelta(minutes=delta_minutes)

        shifted: list[Event] = []
        for event in events:
            start_utc = combine_in_tz(event.day_date, event.start_time, trip_tz)
            if start_utc is None or start_utc < start_from_time:
                continue
            new_start_utc = start_utc + delta
            new_day, new_start = split_in_tz(new_start_utc, trip_tz)
            if new_day != event.day_date:
                # Cross-midnight shift — skip silently in the legacy engine.
                continue
            event.start_time = new_start
            if event.end_time is not None:
                end_utc = combine_in_tz(event.day_date, event.end_time, trip_tz)
                if end_utc is not None:
                    new_end_utc = end_utc + delta
                    new_end_day, new_end = split_in_tz(new_end_utc, trip_tz)
                    if new_end_day == event.day_date:
                        event.end_time = new_end
            shifted.append(event)

        await db.commit()
        return shifted


ripple_engine = RippleEngine()
