"""Intent executor for the Concierge dispatcher.

Maps each classified intent to concrete DB mutations. Called only AFTER
the user confirms the proposed action in the chat drawer.

All datetimes are stored as UTC-aware TIMESTAMPTZ. Wall-clock times from
LLM params are interpreted in the trip's timezone via ``to_utc()``.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import TimelineItem as EventModel, User as UserModel
from app.services.smart_ripple import smart_ripple_engine
from app.utils.tz import utc_now, to_utc, today_in_tz, ensure_utc


_TYPE_TO_CATEGORY: dict[str, str] = {
    "cafe": "Food & Dining",
    "coffee": "Food & Dining",
    "bakery": "Food & Dining",
    "restaurant": "Food & Dining",
    "food": "Food & Dining",
    "bar": "Nightlife",
    "night_club": "Nightlife",
    "museum": "Culture & Arts",
    "art_gallery": "Culture & Arts",
    "park": "Outdoors & Nature",
    "shopping_mall": "Shopping",
    "store": "Shopping",
    "tourist_attraction": "Sightseeing",
    "point_of_interest": "Sightseeing",
    "atm": "Utilities",
    "bank": "Utilities",
    "gas_station": "Utilities",
    "hospital": "Utilities",
    "pharmacy": "Utilities",
}


def _category_from_types(types: list[str]) -> str:
    """Derive a human-friendly category from Google Places type tags."""
    for t in types:
        cat = _TYPE_TO_CATEGORY.get(t)
        if cat:
            return cat
    return "Activity"

log = logging.getLogger(__name__)


def _event_dict(e: EventModel) -> dict[str, Any]:
    """Serialize an Event model to a plain dict for API responses."""
    return {
        "id": e.id,
        "trip_id": e.trip_id,
        "title": e.title,
        "place_id": e.place_id,
        "location_name": e.location_name,
        "lat": e.lat,
        "lng": e.lng,
        "day_date": e.day_date.isoformat() if e.day_date else None,
        "start_time": e.start_time.strftime("%H:%M:%S") if e.start_time else None,
        "end_time": e.end_time.strftime("%H:%M:%S") if e.end_time else None,
        "is_locked": e.is_locked,
        "sort_order": e.sort_order,
        "category": e.category,
        "is_skipped": e.is_skipped,
        "address": e.address,
        "photo_url": e.photo_url,
        "rating": e.rating,
        "price_level": e.price_level,
        "description": e.description,
        "types": e.types,
        "time_category": e.time_category,
        "added_by": e.added_by,
    }


def _parse_time_param(raw: str, trip_tz: str):
    """Parse a time string from LLM params into a naive ``datetime.time``
    in the trip's local wall-clock.

    Handles full ISO datetimes (converted to trip-local then truncated to
    time-of-day) and bare ``HH:MM`` / ``HH:MM:SS`` forms.
    """
    from datetime import datetime, time as _time
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        utc = ensure_utc(dt)
        from app.utils.tz import from_utc
        local = from_utc(utc, trip_tz)
        return local.time().replace(tzinfo=None)
    except ValueError:
        pass
    parts = raw.split(":")
    return _time(
        hour=int(parts[0]),
        minute=int(parts[1]) if len(parts) > 1 else 0,
        second=0,
    )


class ConciergeExecutor:
    """Dispatch confirmed concierge intents to backend mutations."""

    async def execute(
        self,
        intent: str,
        params: dict[str, Any],
        db: AsyncSession,
        trip_id: int,
        user_id: int,
        trip_tz: str = "UTC",
    ) -> dict[str, Any]:
        user = (await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )).scalars().first()
        added_by = user.name if user and user.name else f"user:{user_id}"

        match intent:
            case "skip_event":
                return await self._skip(params, db, trip_id)
            case "shift_timeline":
                return await self._shift(params, db, trip_id, user_id)
            case "move_event":
                return await self._move(params, db, trip_id, trip_tz)
            case "add_event":
                return await self._add(params, db, trip_id, added_by, trip_tz)
            case "find_nearby":
                return await self._add_nearby(params, db, trip_id, user_id, added_by, trip_tz)
            case _:
                return {"success": False, "message": f"Unknown intent: {intent}"}

    async def _skip(
        self, params: dict, db: AsyncSession, trip_id: int,
    ) -> dict[str, Any]:
        event_id = params.get("event_id")
        if not event_id:
            return {"success": False, "message": "Missing event_id"}

        event = (await db.execute(
            select(EventModel).where(
                EventModel.id == event_id,
                EventModel.trip_id == trip_id,
            )
        )).scalars().first()

        if not event:
            return {"success": False, "message": "Event not found"}

        event.is_skipped = True
        await db.commit()
        await db.refresh(event)

        return {
            "success": True,
            "message": f"Skipped **{event.title}**. It'll stay on your timeline but won't affect routing.",
            "updated_events": [_event_dict(event)],
        }

    async def _shift(
        self, params: dict, db: AsyncSession, trip_id: int, user_id: int,
    ) -> dict[str, Any]:
        delta = params.get("delta_minutes", 15)
        event_id = params.get("start_from_event_id")

        shifted = await smart_ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=delta,
            start_from_event_id=event_id,
            user_id=user_id,
        )

        if not shifted:
            return {"success": True, "message": "No events needed shifting.", "updated_events": []}

        names = ", ".join(e.title for e in shifted[:3])
        suffix = f" and {len(shifted) - 3} more" if len(shifted) > 3 else ""
        return {
            "success": True,
            "message": f"Shifted {len(shifted)} event(s): **{names}**{suffix}.",
            "updated_events": [_event_dict(e) for e in shifted],
        }

    async def _move(
        self, params: dict, db: AsyncSession, trip_id: int, trip_tz: str,
    ) -> dict[str, Any]:
        event_id = params.get("event_id")
        if not event_id:
            return {"success": False, "message": "Missing event_id"}

        event = (await db.execute(
            select(EventModel).where(
                EventModel.id == event_id,
                EventModel.trip_id == trip_id,
            )
        )).scalars().first()
        if not event:
            return {"success": False, "message": "Event not found"}

        new_time_str = params.get("new_start_time")
        if new_time_str and event.start_time:
            from datetime import date as _date, datetime as _dt, time as _time
            parts = new_time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            new_start = _time(hour=hour, minute=minute)
            # Preserve duration: compute (end - start) by anchoring on a stub date.
            if event.end_time:
                anchor = _date(2000, 1, 1)
                duration = _dt.combine(anchor, event.end_time) - _dt.combine(anchor, event.start_time)
            else:
                duration = timedelta(hours=1)
            event.start_time = new_start
            event.end_time = (_dt.combine(_date(2000, 1, 1), new_start) + duration).time()

        new_day = params.get("new_day_date")
        if new_day:
            from datetime import date as _date
            event.day_date = _date.fromisoformat(new_day) if isinstance(new_day, str) else new_day

        await db.commit()
        await db.refresh(event)

        local_display = event.start_time.strftime('%I:%M %p') if event.start_time else 'TBD'
        return {
            "success": True,
            "message": f"Moved **{event.title}** to {local_display}.",
            "updated_events": [_event_dict(event)],
        }

    async def _add(
        self, params: dict, db: AsyncSession, trip_id: int,
        added_by: str = "", trip_tz: str = "UTC",
    ) -> dict[str, Any]:
        title = params.get("title")
        if not title:
            return {"success": False, "message": "Missing title"}

        from datetime import date as _date, datetime as _dt
        start_time = None
        end_time = None
        day_date_val = None

        if params.get("start_time"):
            start_time = _parse_time_param(params["start_time"], trip_tz)

        if params.get("end_time"):
            end_time = _parse_time_param(params["end_time"], trip_tz)
        elif start_time:
            # +1h respecting wall-clock, anchored on a stub date to avoid
            # crossing midnight in the TIME arithmetic.
            anchor = _date(2000, 1, 1)
            end_time = (_dt.combine(anchor, start_time) + timedelta(hours=1)).time()

        if params.get("day_date"):
            day_date_val = (
                _date.fromisoformat(params["day_date"])
                if isinstance(params["day_date"], str)
                else params["day_date"]
            )
        else:
            day_date_val = today_in_tz(trip_tz)

        event = EventModel(
            trip_id=trip_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            day_date=day_date_val,
            category=params.get("category"),
            place_id=params.get("place_id"),
            lat=params.get("lat"),
            lng=params.get("lng"),
            address=params.get("address"),
            photo_url=params.get("photo_url"),
            rating=params.get("rating"),
            price_level=params.get("price_level"),
            types=params.get("types"),
            description=params.get("description"),
            added_by=added_by,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        return {
            "success": True,
            "message": f"Added **{event.title}** to your itinerary!",
            "new_event": _event_dict(event),
        }

    async def _add_nearby(
        self, params: dict, db: AsyncSession, trip_id: int, user_id: int,
        added_by: str = "", trip_tz: str = "UTC",
    ) -> dict[str, Any]:
        """Add a place from FindNearby selection. Computes start_time and ripples."""
        title = params.get("title")
        if not title:
            return {"success": False, "message": "Missing place title"}

        from datetime import date as _date, datetime as _dt
        from app.utils.tz import from_utc as _from_utc

        start_time = None
        day_date_val = None
        if params.get("start_time"):
            start_time = _parse_time_param(params["start_time"], trip_tz)
        if not start_time:
            now_local = _from_utc(utc_now() + timedelta(minutes=15), trip_tz)
            start_time = now_local.time().replace(microsecond=0, tzinfo=None)
            day_date_val = now_local.date()

        anchor = _date(2000, 1, 1)
        end_time = (_dt.combine(anchor, start_time) + timedelta(minutes=30)).time()

        types = params.get("types") or []
        category = params.get("category") or _category_from_types(types)

        if day_date_val is None:
            day_date_val = today_in_tz(trip_tz)

        event = EventModel(
            trip_id=trip_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            day_date=day_date_val,
            place_id=params.get("place_id"),
            lat=params.get("lat"),
            lng=params.get("lng"),
            address=params.get("address"),
            photo_url=params.get("photo_url"),
            rating=params.get("rating"),
            price_level=params.get("price_level"),
            types=types or None,
            category=category,
            added_by=added_by,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        from app.utils.tz import combine_in_tz
        shifted = await smart_ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=0,
            start_from_time=combine_in_tz(day_date_val, end_time, trip_tz),
            user_id=user_id,
        )

        updated = [_event_dict(e) for e in shifted] if shifted else []

        return {
            "success": True,
            "message": f"Added **{title}** and adjusted your schedule!",
            "new_event": _event_dict(event),
            "updated_events": updated,
        }


concierge_executor = ConciergeExecutor()
