"""Intent executor for the Concierge dispatcher.

Maps each classified intent to concrete DB mutations. Called only AFTER
the user confirms the proposed action in the chat drawer.

All datetimes are stored as UTC-aware TIMESTAMPTZ. Wall-clock times from
LLM params are interpreted in the trip's timezone via ``to_utc()``.
"""
from __future__ import annotations

import logging
from datetime import timedelta, date
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
        "start_time": e.start_time.isoformat() if e.start_time else None,
        "end_time": e.end_time.isoformat() if e.end_time else None,
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
    """Parse a time string from LLM params into a UTC-aware datetime.

    Handles full ISO strings (with or without 'Z') and bare HH:MM times.
    """
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return ensure_utc(dt)
    except ValueError:
        pass
    parts = raw.split(":")
    now_local = utc_now()
    from app.utils.tz import from_utc
    now_local = from_utc(now_local, trip_tz)
    naive = now_local.replace(
        hour=int(parts[0]),
        minute=int(parts[1]) if len(parts) > 1 else 0,
        second=0, microsecond=0,
    )
    return to_utc(naive.replace(tzinfo=None), trip_tz)


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
            parts = new_time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            duration = (
                (event.end_time - event.start_time)
                if event.end_time else timedelta(hours=1)
            )
            from app.utils.tz import from_utc
            local_st = from_utc(event.start_time, trip_tz)
            new_local = local_st.replace(hour=hour, minute=minute)
            event.start_time = to_utc(new_local.replace(tzinfo=None), trip_tz)
            event.end_time = event.start_time + duration

        new_day = params.get("new_day_date")
        if new_day:
            event.day_date = date.fromisoformat(new_day)

        await db.commit()
        await db.refresh(event)

        from app.utils.tz import from_utc
        local_display = from_utc(event.start_time, trip_tz).strftime('%I:%M %p') if event.start_time else 'TBD'
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

        start_time = None
        end_time = None
        day_date_val = None

        if params.get("start_time"):
            start_time = _parse_time_param(params["start_time"], trip_tz)

        if params.get("end_time"):
            end_time = _parse_time_param(params["end_time"], trip_tz)
        elif start_time:
            end_time = start_time + timedelta(hours=1)

        if params.get("day_date"):
            day_date_val = date.fromisoformat(params["day_date"])
        elif start_time:
            from app.utils.tz import from_utc
            day_date_val = from_utc(start_time, trip_tz).date()
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

        start_time = None
        if params.get("start_time"):
            start_time = _parse_time_param(params["start_time"], trip_tz)
        if not start_time:
            start_time = utc_now() + timedelta(minutes=15)

        end_time = start_time + timedelta(minutes=30)

        types = params.get("types") or []
        category = params.get("category") or _category_from_types(types)

        from app.utils.tz import from_utc
        day_date_val = from_utc(start_time, trip_tz).date()

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

        shifted = await smart_ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=0,
            start_from_time=end_time,
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
