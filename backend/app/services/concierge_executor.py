"""Intent executor for the Concierge dispatcher.

Maps each classified intent to concrete DB mutations. Called only AFTER
the user confirms the proposed action in the chat drawer.

Events store (day_date, start_time, end_time) as (DATE, TIME, TIME) in
trip-local wall-clock (since the datetime rearchitecture, commit 7d0da64).
Wall-clock times from LLM params are parsed in the trip's timezone via
``_parse_time_param``; conversions to/from UTC instants go through
``combine_in_tz`` / ``split_in_tz`` in ``app.utils.tz``.

Write intents that mutate the timeline route their ripple through the
SmartRippleEngine, which (per the engine contract) does NOT commit or roll
back on error — callers own the transaction. See ``app.services.smart_ripple``.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import (
    ConciergeAction,
    TimelineItem as EventModel,
    User as UserModel,
)
from app.services.smart_ripple import (
    CrossMidnightShiftError,
    EventNotEligibleError,
    smart_ripple_engine,
)
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
        record_action: bool = True,
    ) -> dict[str, Any]:
        user = (await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )).scalars().first()
        added_by = user.name if user and user.name else f"user:{user_id}"

        # 3.8: snapshot the timeline before the mutation so we can record an
        # inverse patch for undo. Skipped for non-mutating / unknown intents.
        before = await self._snapshot(db, trip_id) if record_action else None

        match intent:
            case "skip_event":
                result = await self._skip(params, db, trip_id)
            case "shift_timeline":
                result = await self._shift(params, db, trip_id, user_id)
            case "move_event":
                result = await self._move(params, db, trip_id, user_id, trip_tz)
            case "add_event":
                result = await self._add(params, db, trip_id, user_id, added_by, trip_tz)
            case "find_nearby":
                result = await self._add_nearby(params, db, trip_id, user_id, added_by, trip_tz)
            case _:
                return {"success": False, "message": f"Unknown intent: {intent}"}

        if record_action and before is not None and result.get("success"):
            await self._record_action(db, trip_id, user_id, intent, before)

        return result

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

    async def _safe_ripple(
        self, db: AsyncSession, *, trip_id: int, user_id: int,
        delta_minutes: int, start_from_event_id: Optional[int] = None,
        start_from_time=None,
    ) -> tuple[list[EventModel], Optional[str]]:
        """Run a committing ripple, converting a CrossMidnightShiftError into a
        partial-commit warning (A3). Returns ``(shifted_events, warning|None)``.

        On the overnight boundary the engine re-raises with ``shifted_so_far``
        without committing; we commit those partial shifts and warn the user
        rather than 500-ing or losing the work.
        """
        try:
            shifted = await smart_ripple_engine.shift_itinerary(
                db=db,
                trip_id=trip_id,
                delta_minutes=delta_minutes,
                start_from_event_id=start_from_event_id,
                start_from_time=start_from_time,
                user_id=user_id,
            )
            return shifted, None
        except CrossMidnightShiftError as exc:
            await db.commit()
            n = len(exc.shifted_so_far)
            warning = (
                f"I shifted {n} event(s), but the next one would run past midnight, "
                "so I stopped there."
            )
            return exc.shifted_so_far, warning

    async def _shift(
        self, params: dict, db: AsyncSession, trip_id: int, user_id: int,
    ) -> dict[str, Any]:
        delta = params.get("delta_minutes", 15)
        event_id = params.get("start_from_event_id")

        try:
            shifted, warning = await self._safe_ripple(
                db, trip_id=trip_id, user_id=user_id,
                delta_minutes=delta, start_from_event_id=event_id,
            )
        except EventNotEligibleError as exc:
            # A4: the user asked to shift from a specific event that can't anchor
            # — explain precisely instead of a misleading "nothing to shift".
            return {"success": False, "message": exc.user_message, "updated_events": []}

        if warning:
            return {
                "success": True,
                "message": warning,
                "updated_events": [_event_dict(e) for e in shifted],
            }

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
        self, params: dict, db: AsyncSession, trip_id: int, user_id: int,
        trip_tz: str = "UTC",
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

        # A7: cross-day moves aren't supported via chat — the cascade is same-day.
        new_day = params.get("new_day_date")
        if new_day:
            from datetime import date as _date
            new_day_date = _date.fromisoformat(new_day) if isinstance(new_day, str) else new_day
            if new_day_date != event.day_date:
                return {
                    "success": False,
                    "message": (
                        "Cross-day moves aren't supported via chat yet — drag the "
                        "event to the new day from the timeline."
                    ),
                }

        new_time_str = params.get("new_start_time")
        if not new_time_str:
            return {"success": False, "message": "No new time given for the move."}

        from datetime import date as _date, datetime as _dt, time as _time
        parts = new_time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        new_start = _time(hour=hour, minute=minute)

        # B-5: previously a null start_time silently dropped the move. Now we set
        # it, defaulting the duration to 1h when there was no prior window.
        stub = _date(2000, 1, 1)
        if event.start_time and event.end_time:
            duration = _dt.combine(stub, event.end_time) - _dt.combine(stub, event.start_time)
        else:
            duration = timedelta(hours=1)
        event.start_time = new_start
        event.end_time = (_dt.combine(stub, new_start) + duration).time()

        await db.commit()
        await db.refresh(event)

        # A7: re-ripple downstream events from the moved event so travel-time
        # conflicts created by the move cascade correctly.
        shifted, warning = await self._safe_ripple(
            db, trip_id=trip_id, user_id=user_id,
            delta_minutes=0, start_from_event_id=event.id,
        )

        # Merge the moved event with any downstream shifts (dedupe by id).
        merged: dict[int, EventModel] = {event.id: event}
        for e in shifted:
            merged[e.id] = e

        local_display = event.start_time.strftime('%I:%M %p')
        base_msg = f"Moved **{event.title}** to {local_display}."
        message = f"{base_msg} {warning}" if warning else base_msg
        return {
            "success": True,
            "message": message,
            "updated_events": [_event_dict(e) for e in merged.values()],
        }

    async def _add(
        self, params: dict, db: AsyncSession, trip_id: int, user_id: int,
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

        # A8: an event inserted between two existing events must push the later
        # one to make room for travel — ripple anchored on the new event.
        updated_events: list[dict[str, Any]] = []
        message = f"Added **{event.title}** to your itinerary!"
        if event.start_time is not None:
            shifted, warning = await self._safe_ripple(
                db, trip_id=trip_id, user_id=user_id,
                delta_minutes=0, start_from_event_id=event.id,
            )
            updated_events = [_event_dict(e) for e in shifted]
            if warning:
                message = f"{message} {warning}"

        return {
            "success": True,
            "message": message,
            "new_event": _event_dict(event),
            "updated_events": updated_events,
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

        # A1: anchor the ripple on the inserted event itself so the P -> next leg
        # is actually evaluated. (The old code anchored on the *next* event with
        # delta=0, so the critical travel leg was never measured and nothing
        # moved.) The inserted event is unchanged (delta=0), so _record_shift
        # keeps it out of ``shifted`` — only genuinely pushed events come back.
        shifted, warning = await self._safe_ripple(
            db, trip_id=trip_id, user_id=user_id,
            delta_minutes=0, start_from_event_id=event.id,
        )

        updated = [_event_dict(e) for e in shifted] if shifted else []
        message = f"Added **{title}** and adjusted your schedule!"
        if warning:
            message = f"Added **{title}**. {warning}"

        return {
            "success": True,
            "message": message,
            "new_event": _event_dict(event),
            "updated_events": updated,
        }

    # ── 3.8 Undo: snapshot / record / revert ─────────────────────────────────

    @staticmethod
    def _event_state(e: EventModel) -> dict[str, Any]:
        """JSON-serialisable snapshot of the fields a Concierge action can change."""
        return {
            "day_date": e.day_date.isoformat() if e.day_date else None,
            "start_time": e.start_time.strftime("%H:%M:%S") if e.start_time else None,
            "end_time": e.end_time.strftime("%H:%M:%S") if e.end_time else None,
            "is_skipped": bool(e.is_skipped),
        }

    async def _snapshot(self, db: AsyncSession, trip_id: int) -> dict[int, dict[str, Any]]:
        rows = (await db.execute(
            select(EventModel).where(EventModel.trip_id == trip_id)
        )).scalars().all()
        return {e.id: self._event_state(e) for e in rows}

    async def _record_action(
        self, db: AsyncSession, trip_id: int, user_id: int,
        intent: str, before: dict[int, dict[str, Any]],
    ) -> None:
        """Diff the post-mutation timeline against ``before`` and persist an
        inverse patch so the action can be undone (3.8). Events present only
        after the action (adds) invert to a delete; changed events invert to
        their prior state."""
        after = await self._snapshot(db, trip_id)
        changes: list[dict[str, Any]] = []
        for eid, after_state in after.items():
            if eid not in before:
                changes.append({"event_id": eid, "op": "delete"})
            elif before[eid] != after_state:
                changes.append({"event_id": eid, "op": "restore", **before[eid]})
        if not changes:
            return
        db.add(ConciergeAction(
            trip_id=trip_id, user_id=user_id, intent=intent,
            inverse_patch={"changes": changes},
        ))
        await db.commit()

    async def undo(
        self, db: AsyncSession, trip_id: int, user_id: int,
    ) -> dict[str, Any]:
        """Revert the most recent not-yet-undone Concierge action (3.8)."""
        from datetime import date as _date, time as _time

        action = (await db.execute(
            select(ConciergeAction)
            .where(
                ConciergeAction.trip_id == trip_id,
                ConciergeAction.undone_at.is_(None),
            )
            .order_by(ConciergeAction.created_at.desc())
            .limit(1)
        )).scalars().first()

        if action is None:
            return {"success": False, "message": "Nothing to undo.", "updated_events": []}

        patch = (action.inverse_patch or {}).get("changes", [])
        restored: list[EventModel] = []

        def _parse_time(v):
            if not v:
                return None
            parts = v.split(":")
            return _time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0,
                         int(parts[2]) if len(parts) > 2 else 0)

        for ch in patch:
            event = (await db.execute(
                select(EventModel).where(
                    EventModel.id == ch.get("event_id"),
                    EventModel.trip_id == trip_id,
                )
            )).scalars().first()
            if event is None:
                continue
            if ch.get("op") == "delete":
                await db.delete(event)
                continue
            # op == "restore"
            event.day_date = _date.fromisoformat(ch["day_date"]) if ch.get("day_date") else None
            event.start_time = _parse_time(ch.get("start_time"))
            event.end_time = _parse_time(ch.get("end_time"))
            event.is_skipped = bool(ch.get("is_skipped"))
            restored.append(event)

        action.undone_at = utc_now()
        await db.commit()
        for e in restored:
            await db.refresh(e)

        return {
            "success": True,
            "message": "Reverted the last action.",
            "updated_events": [_event_dict(e) for e in restored],
            "undone_action_id": action.id,
        }

    # ── 3.5 / 3.6 Dry-run preview ────────────────────────────────────────────

    async def preview(
        self, intent: str, params: dict[str, Any], db: AsyncSession,
        trip_id: int, user_id: int, trip_tz: str = "UTC",
    ):
        """Compute the real projected impact of a pending write via a dry-run
        ripple inside a rolled-back SAVEPOINT — nothing persists. Returns a
        ``ConciergePreview`` or ``None`` when the intent has no timeline impact."""
        from app.schemas.concierge import (
            ConciergePreview, PreviewChange, PreviewWarning,
        )
        from datetime import date as _date, datetime as _dt, time as _time

        if intent not in ("shift_timeline", "move_event", "add_event"):
            return None

        def _hhmm(t) -> Optional[str]:
            return t.strftime("%H:%M") if t else None

        def _proj_change(p) -> PreviewChange:
            return PreviewChange(
                event_id=p.event_id, title=p.title,
                day_date=p.day_date.isoformat() if p.day_date else None,
                old_start=_hhmm(p.old_start), new_start=_hhmm(p.new_start),
                old_end=_hhmm(p.old_end), new_end=_hhmm(p.new_end),
            )

        sp = await db.begin_nested()
        try:
            anchor_change: Optional[PreviewChange] = None
            result = None

            if intent == "shift_timeline":
                try:
                    result = await smart_ripple_engine.shift_itinerary(
                        db=db, trip_id=trip_id,
                        delta_minutes=params.get("delta_minutes", 15),
                        start_from_event_id=params.get("start_from_event_id"),
                        user_id=user_id, dry_run=True,
                    )
                except EventNotEligibleError as exc:
                    return ConciergePreview(
                        summary=exc.user_message, changes=[],
                        warnings=[PreviewWarning(kind="ineligible", message=exc.user_message)],
                    )

            elif intent == "move_event":
                event = (await db.execute(
                    select(EventModel).where(
                        EventModel.id == params.get("event_id"),
                        EventModel.trip_id == trip_id,
                    )
                )).scalars().first()
                if event is None:
                    return None
                new_day = params.get("new_day_date")
                if new_day:
                    nd = _date.fromisoformat(new_day) if isinstance(new_day, str) else new_day
                    if nd != event.day_date:
                        return ConciergePreview(
                            summary="Cross-day moves aren't supported via chat — drag it on the timeline.",
                            changes=[],
                            warnings=[PreviewWarning(
                                kind="cross_day", event_id=event.id,
                                message="Cross-day moves aren't supported via chat.",
                            )],
                        )
                new_time_str = params.get("new_start_time")
                if not new_time_str:
                    return None
                parts = new_time_str.split(":")
                new_start = _time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
                old_start, old_end = event.start_time, event.end_time
                stub = _date(2000, 1, 1)
                if event.start_time and event.end_time:
                    dur = _dt.combine(stub, event.end_time) - _dt.combine(stub, event.start_time)
                else:
                    dur = timedelta(hours=1)
                event.start_time = new_start
                event.end_time = (_dt.combine(stub, new_start) + dur).time()
                await db.flush()
                anchor_change = PreviewChange(
                    event_id=event.id, title=event.title,
                    day_date=event.day_date.isoformat() if event.day_date else None,
                    old_start=_hhmm(old_start), new_start=_hhmm(event.start_time),
                    old_end=_hhmm(old_end), new_end=_hhmm(event.end_time),
                )
                result = await smart_ripple_engine.shift_itinerary(
                    db=db, trip_id=trip_id, delta_minutes=0,
                    start_from_event_id=event.id, user_id=user_id, dry_run=True,
                )

            elif intent == "add_event":
                title = params.get("title")
                if not title or not params.get("start_time"):
                    return None
                start_time = _parse_time_param(params["start_time"], trip_tz)
                if params.get("end_time"):
                    end_time = _parse_time_param(params["end_time"], trip_tz)
                else:
                    stub = _date(2000, 1, 1)
                    end_time = (_dt.combine(stub, start_time) + timedelta(hours=1)).time()
                day_date_val = (
                    _date.fromisoformat(params["day_date"])
                    if isinstance(params.get("day_date"), str) else params.get("day_date")
                ) or today_in_tz(trip_tz)
                event = EventModel(
                    trip_id=trip_id, title=title, start_time=start_time,
                    end_time=end_time, day_date=day_date_val,
                    category=params.get("category"), place_id=params.get("place_id"),
                    lat=params.get("lat"), lng=params.get("lng"),
                )
                db.add(event)
                await db.flush()
                anchor_change = PreviewChange(
                    event_id=event.id, title=event.title,
                    day_date=day_date_val.isoformat() if day_date_val else None,
                    old_start=None, new_start=_hhmm(start_time),
                    old_end=None, new_end=_hhmm(end_time),
                )
                result = await smart_ripple_engine.shift_itinerary(
                    db=db, trip_id=trip_id, delta_minutes=0,
                    start_from_event_id=event.id, user_id=user_id, dry_run=True,
                )

            changes: list[PreviewChange] = []
            if anchor_change is not None:
                changes.append(anchor_change)
            changes.extend(_proj_change(p) for p in result.projected)
            warnings = [
                PreviewWarning(kind=w.kind, message=w.message, event_id=w.event_id)
                for w in result.warnings
            ]
            n = len(changes)
            summary = (
                f"Adjusts {n} event(s)" if n != 1 else "Adjusts 1 event"
            )
            if not changes and not warnings:
                summary = "No timeline changes needed."
            return ConciergePreview(summary=summary, changes=changes, warnings=warnings)
        except Exception:  # noqa: BLE001 — preview must never break the chat turn
            log.warning("Concierge preview failed for intent=%s", intent, exc_info=True)
            return None
        finally:
            await sp.rollback()


concierge_executor = ConciergeExecutor()
