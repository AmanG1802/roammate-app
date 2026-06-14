"""Concierge API endpoints.

Six endpoints covering the hybrid LLM + direct-API chat surface:
  - POST /{trip_id}/chat        -- LLM dispatch (free-text)
  - POST /{trip_id}/execute     -- confirm and execute (no LLM)
  - POST /{trip_id}/find-nearby -- Google Maps nearby search (no LLM)
  - POST /{trip_id}/skip-event  -- soft-skip an event (no LLM)
  - GET  /{trip_id}/whats-next  -- next event data query (no LLM)
  - GET  /{trip_id}/today-summary -- today's events summary (no LLM)
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import date as _date, timedelta

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.all_models import (
    ConciergeMessage,
    TimelineItem as EventModel,
    Trip as TripModel,
    User,
)
from app.schemas.concierge import (
    ConciergeChatRequest,
    ConciergeChatResponse,
    ConciergeMessageOut,
    ConciergeThreadResponse,
    ExecuteRequest,
    ExecuteResponse,
    FindNearbyRequest,
    FindNearbyResponse,
    PlaceCard,
    SkipEventRequest,
    TodaySummaryEvent,
    TodaySummaryResponse,
    UndoResponse,
    WhatsNextResponse,
)
from app.services.concierge_executor import concierge_executor
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.services.llm.registry import get_concierge_client
from app.services.roles import require_trip_member, require_trip_editor, get_trip_member
from app.services import entitlements
from app.utils.tz import utc_now, from_utc, today_in_tz, combine_in_tz

log = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_trip_tz(db: AsyncSession, trip_id: int) -> str:
    """Load the trip's IANA timezone string, defaulting to UTC."""
    trip = (await db.execute(
        select(TripModel).where(TripModel.id == trip_id)
    )).scalars().first()
    return (trip.timezone if trip and trip.timezone else "UTC")


def _trip_is_active(trip: Optional[TripModel], trip_tz: str) -> bool:
    """True when today (in the trip's tz) falls within ``[start_date, end_date]``.

    Trip day boundaries follow the stored datetime's *date* component, matching
    how ``TripDay.date`` is derived elsewhere (see ``trips.py``)."""
    if trip is None or trip.start_date is None or trip.end_date is None:
        return False
    today = today_in_tz(trip_tz)
    start = trip.start_date.date() if hasattr(trip.start_date, "date") else trip.start_date
    end = trip.end_date.date() if hasattr(trip.end_date, "date") else trip.end_date
    return start <= today <= end


async def _enrich_add_event_params(
    params: dict, trip: Optional[TripModel], user_id: int, trip_id: int,
) -> dict:
    """Hydrate ``add_event`` params with Maps data (lat/lng/place_id/address…)
    so the new event is route-eligible from the start and the confirmation card
    can preview the real location. Idempotent — skips when ``place_id`` is set.

    Biases ``find_place`` to the trip destination when known. Failures are
    swallowed (the event is still added, just without coordinates)."""
    if not params or params.get("place_id") or not params.get("title"):
        return params
    from app.services.google_maps.base import LocationContext

    maps_service = get_google_maps_service()
    maps_service._current_user_id = user_id
    maps_service._current_trip_id = trip_id
    loc = None
    if trip is not None and trip.destination_lat and trip.destination_lng:
        loc = LocationContext(lat=trip.destination_lat, lng=trip.destination_lng)
    try:
        return await maps_service.enrich_item(dict(params), location=loc)
    except Exception:
        log.warning("add_event enrichment failed for %r", params.get("title"), exc_info=True)
        return params


def _event_dict_for_response(e: EventModel) -> dict:
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
        "is_skipped": e.is_skipped,
        "category": e.category,
        "address": e.address,
        "photo_url": e.photo_url,
        "rating": e.rating,
        "price_level": e.price_level,
        "sort_order": e.sort_order,
        "description": e.description,
        "types": e.types,
        "time_category": e.time_category,
        "added_by": e.added_by,
    }


async def _load_today_events(
    db: AsyncSession, trip_id: int, trip_tz: str,
) -> list[EventModel]:
    today = today_in_tz(trip_tz)
    stmt = (
        select(EventModel)
        .where(
            EventModel.trip_id == trip_id,
            EventModel.day_date == today,
        )
        .order_by(EventModel.start_time.asc().nulls_last())
    )
    return list((await db.execute(stmt)).scalars().all())


def _build_events_list(events: list[EventModel], trip_tz: str) -> str:
    del trip_tz  # start/end_time are already trip-local wall-clock TIMEs
    if not events:
        return "No events scheduled today."
    lines = []
    for e in events:
        st = e.start_time.strftime("%H:%M") if e.start_time else "TBD"
        et = e.end_time.strftime("%H:%M") if e.end_time else "TBD"
        loc = e.address or e.location_name or ""
        skipped = " [SKIPPED]" if e.is_skipped else ""
        lines.append(f"[id={e.id}] {st}-{et} | {e.title} | {e.category or 'General'} | {loc}{skipped}")
    return "\n".join(lines)


def _format_hours_for_day(opening_hours: Optional[dict], day_date) -> Optional[str]:
    """Compact 'open–close' string for a day, or None when unknown."""
    if not opening_hours or not isinstance(opening_hours, dict) or day_date is None:
        return None
    periods = opening_hours.get("periods")
    if not periods:
        return None
    gday = (day_date.weekday() + 1) % 7

    def _fmt(point: dict) -> Optional[str]:
        if "hour" in point:
            return f"{int(point.get('hour', 0)):02d}:{int(point.get('minute', 0)):02d}"
        raw = point.get("time")
        if isinstance(raw, str) and len(raw) == 4 and raw.isdigit():
            return f"{raw[:2]}:{raw[2:]}"
        return None

    for p in periods:
        if not isinstance(p, dict):
            continue
        op = p.get("open") or {}
        if op.get("day") != gday:
            continue
        o = _fmt(op)
        cl = p.get("close") or {}
        c = _fmt(cl) if isinstance(cl, dict) else None
        if o and c:
            return f"{o}-{c}"
        if o:
            return f"opens {o}"
    return None


async def _load_trip_events_grouped(
    db: AsyncSession, trip_id: int,
) -> "OrderedDict[_date, list[EventModel]]":
    """Whole-trip events grouped by day, each day ordered by start_time (B-2/3.3)."""
    stmt = (
        select(EventModel)
        .where(EventModel.trip_id == trip_id, EventModel.day_date.is_not(None))
        .order_by(EventModel.day_date.asc(), EventModel.start_time.asc().nulls_last())
    )
    grouped: "OrderedDict[_date, list[EventModel]]" = OrderedDict()
    for e in (await db.execute(stmt)).scalars().all():
        grouped.setdefault(e.day_date, []).append(e)
    return grouped


def _build_multiday_events_list(
    events_by_day: "OrderedDict[_date, list[EventModel]]",
    today,
    near_window_days: int = 2,
) -> str:
    """Render whole-trip events with day headers. Days within ``near_window_days``
    of today render in full (with opening hours when known); distant days are
    summarised to a count to respect the token budget (3.3)."""
    if not events_by_day:
        return "No events scheduled."
    out: list[str] = []
    for idx, (day, events) in enumerate(events_by_day.items(), start=1):
        marker = " (today)" if day == today else ""
        header = f"Day {idx} — {day.isoformat()}{marker}"
        distant = abs((day - today).days) > near_window_days
        if distant:
            out.append(f"{header}: {len(events)} event(s) (summary only)")
            continue
        out.append(header)
        if not events:
            out.append("  (no events)")
            continue
        for e in events:
            st = e.start_time.strftime("%H:%M") if e.start_time else "TBD"
            et = e.end_time.strftime("%H:%M") if e.end_time else "TBD"
            loc = e.address or e.location_name or ""
            skipped = " [SKIPPED]" if e.is_skipped else ""
            hours = _format_hours_for_day(getattr(e, "opening_hours", None), day)
            hours_str = f" | hours {hours}" if hours else ""
            out.append(
                f"  [id={e.id}] {st}-{et} | {e.title} | {e.category or 'General'} | {loc}{hours_str}{skipped}"
            )
    return "\n".join(out)


async def _build_travel_times(
    db: AsyncSession, trip_id: int,
    events_by_day: "OrderedDict[_date, list[EventModel]]",
    user_id: int,
) -> str:
    """Real per-leg driving minutes between consecutive same-day events (3.2 /
    fixes B-1). Reuses stored DayRoute legs first (B2), falling back to a cached
    directions() call, so the LLM reasons over real travel data."""
    from app.services.smart_ripple import SmartRippleEngine

    maps_service = get_google_maps_service()
    lines: list[str] = []
    for day, events in events_by_day.items():
        active = [
            e for e in events
            if not e.is_skipped and e.start_time
            and (e.place_id or (e.lat is not None and e.lng is not None))
        ]
        if len(active) < 2:
            continue
        memo = await SmartRippleEngine._load_leg_memo(db, trip_id, day)
        for prev, curr in zip(active, active[1:]):
            mins = memo.get((prev.id, curr.id))
            if mins is None:
                p1 = SmartRippleEngine._event_to_route_point(prev)
                p2 = SmartRippleEngine._event_to_route_point(curr)
                if p1 and p2:
                    try:
                        route = await maps_service.directions(
                            [p1, p2], user_id=user_id, trip_id=trip_id,
                        )
                        if route and route.legs:
                            mins = route.legs[0].duration_s / 60.0
                    except Exception:
                        log.warning("travel-time context failed for %s -> %s", prev.id, curr.id)
            if mins is not None:
                lines.append(f"{prev.title} -> {curr.title}: {round(mins)} min")
    return "\n".join(lines) if lines else "No travel time data available."


async def _persist_message(
    db: AsyncSession, trip_id: int, user_id: int,
    role: str, content: str,
    message_type: str = "text", metadata: dict | None = None,
):
    msg = ConciergeMessage(
        trip_id=trip_id,
        user_id=user_id,
        role=role,
        content=content,
        message_type=message_type,
        metadata_=metadata,
    )
    db.add(msg)
    await db.commit()


async def _can_write_concierge(db: AsyncSession, trip_id: int, user: User) -> bool:
    """A member may post / confirm only if they're a trip editor (admin in v1)
    AND Plus. Used to set the read-only flag on the shared thread (3.1)."""
    member = await get_trip_member(db, trip_id, user.id)
    if member is None or member.role != "admin":
        return False
    try:
        ent = await entitlements.get_entitlement(db, user)
    except Exception:
        return False
    return bool(ent.can_use_concierge)


async def _author_names(db: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    """Map user_id → display name for message authors."""
    if not user_ids:
        return {}
    rows = (await db.execute(
        select(User.id, User.name).where(User.id.in_(user_ids))
    )).all()
    return {r[0]: (r[1] or f"user:{r[0]}") for r in rows}


async def _load_history(
    db: AsyncSession, trip_id: int, limit: int = 10,
) -> list[dict[str, str]]:
    """Trip-wide LLM history (3.1). The thread is shared by the whole group, so
    we scope by trip only and prefix each user turn with its author so the model
    knows who said what (e.g. "Aman: push dinner back")."""
    stmt = (
        select(ConciergeMessage)
        .where(
            ConciergeMessage.trip_id == trip_id,
            ConciergeMessage.role.in_(["user", "assistant"]),
        )
        .order_by(ConciergeMessage.created_at.desc())
        .limit(limit)
    )
    messages = list((await db.execute(stmt)).scalars().all())
    messages.reverse()
    names = await _author_names(db, {m.user_id for m in messages if m.role == "user"})
    history: list[dict[str, str]] = []
    for m in messages:
        content = m.content
        if m.role == "user":
            content = f"{names.get(m.user_id, 'Member')}: {content}"
        history.append({"role": m.role, "content": content})
    return history


# ── 1. POST /{trip_id}/chat — LLM dispatch ──────────────────────────────────

@router.post("/{trip_id}/chat", response_model=ConciergeChatResponse)
async def concierge_chat(
    trip_id: int,
    body: ConciergeChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 3.1: posting to the shared thread requires edit rights (admin in v1) AND
    # Plus. Reading the thread (GET /messages) is open to all members.
    await require_trip_editor(db, trip_id, current_user.id)
    trip = (await db.execute(select(TripModel).where(TripModel.id == trip_id))).scalars().first()
    if trip is not None and trip.is_tutorial_completed:
        raise HTTPException(status_code=423, detail={"code": "tutorial_locked"})
    await entitlements.enforce_concierge(db, current_user, trip=trip)

    if trip is not None and trip.is_tutorial:
        from app.services.tutorial_fixtures import CANNED_CONCIERGE_REPLIES
        prior = await _load_history(db, trip_id)
        idx = len([m for m in prior if m.get("role") == "user"])
        canned = CANNED_CONCIERGE_REPLIES[idx % len(CANNED_CONCIERGE_REPLIES)]
        await _persist_message(db, trip_id, current_user.id, "user", body.message)
        await _persist_message(
            db, trip_id, current_user.id, "assistant", canned, message_type="text",
        )
        return ConciergeChatResponse(
            intent="chat_only",
            user_message=canned,
            params={},
            requires_confirmation=False,
            message_type="text",
        )

    trip_tz = await _get_trip_tz(db, trip_id)
    now = utc_now()
    local_now = from_utc(now, trip_tz)

    today = today_in_tz(trip_tz)
    events_by_day = await _load_trip_events_grouped(db, trip_id)
    events_list = _build_multiday_events_list(events_by_day, today)
    travel_times = await _build_travel_times(db, trip_id, events_by_day, current_user.id)
    current_time = local_now.strftime("%Y-%m-%d %H:%M")

    history = await _load_history(db, trip_id)

    client = get_concierge_client()
    result = await client.dispatch(
        history=history,
        user_message=body.message,
        trip_context={
            "events_list": events_list,
            "travel_times": travel_times,
            "current_time": current_time,
            "trip_id": trip_id,
        },
        user_id=current_user.id,
    )

    # Date-gate real-time-only intents (running late / skip / find nearby): these
    # only make sense while the trip is in progress. Return a friendly text turn
    # instead of an action card when today is outside the trip window.
    if (
        concierge_executor.is_active_trip_only_intent(result.get("intent"))
        and not _trip_is_active(trip, trip_tz)
    ):
        blocked = "That action is only available while the trip is running."
        await _persist_message(db, trip_id, current_user.id, "user", body.message)
        await _persist_message(
            db, trip_id, current_user.id, "assistant", blocked, message_type="text",
        )
        return ConciergeChatResponse(
            intent="chat_only",
            user_message=blocked,
            params={},
            requires_confirmation=False,
            message_type="text",
        )

    # For a confirmable add_event, enrich the params with Maps data now (during
    # the LLM dispatch/dry-run step, before the action card is shown) so the
    # preview displays the real address and the committed event is route-eligible
    # immediately on confirm.
    if result.get("intent") == "add_event" and result.get("requires_confirmation"):
        result["params"] = await _enrich_add_event_params(
            result.get("params", {}), trip, current_user.id, trip_id,
        )

    await _persist_message(db, trip_id, current_user.id, "user", body.message)
    await _persist_message(
        db, trip_id, current_user.id, "assistant",
        result.get("user_message", ""),
        message_type="action_card" if result.get("requires_confirmation") else "text",
        metadata={"intent": result.get("intent"), "params": result.get("params")},
    )

    message_type = "text"
    if result.get("requires_confirmation"):
        message_type = "action_card"
    if result.get("intent") == "find_nearby":
        message_type = "place_card"
    if result.get("params", {}).get("retry"):
        message_type = "error"

    # 3.5/3.6: for a pending timeline write, compute the real projected impact
    # via a rolled-back dry-run ripple so the action card can show a true
    # before→after diff and feasibility warnings (incl. opening hours, 3.7).
    preview = None
    if result.get("requires_confirmation"):
        preview = await concierge_executor.preview(
            intent=result["intent"],
            params=result.get("params", {}),
            db=db,
            trip_id=trip_id,
            user_id=current_user.id,
            trip_tz=trip_tz,
        )

    return ConciergeChatResponse(
        intent=result["intent"],
        user_message=result["user_message"],
        params=result.get("params", {}),
        requires_confirmation=result.get("requires_confirmation", True),
        message_type=message_type,
        preview=preview,
    )


# ── 2. POST /{trip_id}/execute — confirm & execute ──────────────────────────

@router.post("/{trip_id}/execute", response_model=ExecuteResponse)
async def concierge_execute(
    trip_id: int,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # A2: confirming an action mutates the timeline — gate it like the REST
    # ripple (editor == admin in v1), not merely trip membership.
    await require_trip_editor(db, trip_id, current_user.id)
    trip = (await db.execute(select(TripModel).where(TripModel.id == trip_id))).scalars().first()
    await entitlements.enforce_concierge(db, current_user, trip=trip)

    trip_tz = await _get_trip_tz(db, trip_id)

    result = await concierge_executor.execute(
        intent=body.intent,
        params=body.params,
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
        trip_tz=trip_tz,
    )

    await _persist_message(
        db, trip_id, current_user.id, "system",
        f"Action confirmed: {result.get('message', '')}",
        message_type="text",
    )

    return ExecuteResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        updated_events=result.get("updated_events"),
        new_event=result.get("new_event"),
    )


# ── 3. POST /{trip_id}/find-nearby — Google Maps (no LLM) ───────────────────

@router.post("/{trip_id}/find-nearby", response_model=FindNearbyResponse)
async def find_nearby(
    trip_id: int,
    body: FindNearbyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)
    await entitlements.enforce_concierge(db, current_user)

    maps_service = get_google_maps_service()
    maps_service._current_user_id = current_user.id
    maps_service._current_trip_id = trip_id
    raw_places = await maps_service.nearby_search(
        query=body.query,
        lat=body.lat,
        lng=body.lng,
        limit=body.limit,
    )

    places: list[PlaceCard] = []
    for p in raw_places:
        travel_time_s = None
        distance_m = None

        p_lat = p.get("lat")
        p_lng = p.get("lng")
        p_place_id = p.get("place_id")

        if p_lat and p_lng:
            origin = RoutePoint(lat=body.lat, lng=body.lng)
            dest = RoutePoint(
                place_id=p_place_id if p_place_id else None,
                lat=p_lat, lng=p_lng,
            )
            try:
                route = await maps_service.directions(
                    [origin, dest],
                    user_id=current_user.id,
                    trip_id=trip_id,
                )
                if route and route.legs:
                    travel_time_s = route.legs[0].duration_s
                    distance_m = route.legs[0].distance_m
            except Exception:
                log.warning("Failed to compute travel time to %s", p.get("title"))

        places.append(PlaceCard(
            place_id=p.get("place_id", ""),
            title=p.get("title", ""),
            address=p.get("address"),
            lat=p_lat or 0,
            lng=p_lng or 0,
            rating=p.get("rating"),
            price_level=p.get("price_level"),
            photo_url=p.get("photo_url"),
            types=p.get("types"),
            category=body.category,
            travel_time_s=travel_time_s,
            distance_m=distance_m,
        ))

    total = len(raw_places)
    enriched_count = sum(1 for p in places if p.place_id)
    skipped_count = total - enriched_count
    from app.schemas.enrichment import EnrichmentStatus
    enr = None
    if skipped_count > 0:
        enr = EnrichmentStatus(
            status="partial" if enriched_count > 0 else "none",
            total=total,
            enriched=enriched_count,
            skipped=skipped_count,
        )
    return FindNearbyResponse(places=places, enrichment=enr)


# ── 4. POST /{trip_id}/skip-event — soft skip (no LLM) ──────────────────────

@router.post("/{trip_id}/skip-event", response_model=ExecuteResponse)
async def skip_event(
    trip_id: int,
    body: SkipEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # A2: skipping an event is a timeline mutation — same editor gate.
    await require_trip_editor(db, trip_id, current_user.id)
    trip = (await db.execute(select(TripModel).where(TripModel.id == trip_id))).scalars().first()
    await entitlements.enforce_concierge(db, current_user, trip=trip)

    result = await concierge_executor.execute(
        intent="skip_event",
        params={"event_id": body.event_id},
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    if result.get("success"):
        await _persist_message(
            db, trip_id, current_user.id, "system",
            result.get("message", "Event skipped."),
        )

    return ExecuteResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        updated_events=result.get("updated_events"),
    )


# ── 5. GET /{trip_id}/whats-next — pure data query (no LLM) ─────────────────

@router.get("/{trip_id}/whats-next", response_model=WhatsNextResponse)
async def whats_next(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)

    trip_tz = await _get_trip_tz(db, trip_id)
    now = utc_now()

    events = await _load_today_events(db, trip_id, trip_tz)
    active = [e for e in events if not e.is_skipped and e.start_time]

    current_event = None
    next_event = None
    next_event_start_utc = None

    for e in active:
        start_utc = combine_in_tz(e.day_date, e.start_time, trip_tz)
        if start_utc is None:
            continue
        end_utc = combine_in_tz(e.day_date, e.end_time, trip_tz) or (start_utc + timedelta(hours=1))
        if start_utc <= now <= end_utc:
            current_event = e
        elif start_utc > now and next_event is None:
            next_event = e
            next_event_start_utc = start_utc

    time_until = None
    travel_time = None

    if next_event and next_event_start_utc is not None:
        delta = next_event_start_utc - now
        minutes = int(delta.total_seconds() / 60)
        if minutes >= 60:
            time_until = f"{minutes // 60}h {minutes % 60}m"
        else:
            time_until = f"{minutes}m"

        if current_event:
            maps_service = get_google_maps_service()
            from app.services.smart_ripple import SmartRippleEngine
            prev_pt = SmartRippleEngine._event_to_route_point(current_event)
            next_pt = SmartRippleEngine._event_to_route_point(next_event)
            if prev_pt and next_pt:
                try:
                    route = await maps_service.directions(
                        [prev_pt, next_pt],
                        user_id=current_user.id,
                        trip_id=trip_id,
                    )
                    if route and route.legs:
                        travel_time = route.legs[0].duration_s
                except Exception:
                    pass

    return WhatsNextResponse(
        current_event=_event_dict_for_response(current_event) if current_event else None,
        next_event=_event_dict_for_response(next_event) if next_event else None,
        time_until_next=time_until,
        travel_time_to_next=travel_time,
    )


# ── 6. GET /{trip_id}/today-summary — data query (no LLM) ───────────────────

@router.get("/{trip_id}/today-summary", response_model=TodaySummaryResponse)
async def today_summary(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)

    trip_tz = await _get_trip_tz(db, trip_id)
    now = utc_now()
    today = today_in_tz(trip_tz)
    events = await _load_today_events(db, trip_id, trip_tz)

    summary_events: list[TodaySummaryEvent] = []
    completed = 0
    upcoming = 0
    skipped = 0

    for e in events:
        end_utc = combine_in_tz(e.day_date, e.end_time, trip_tz)
        start_utc = combine_in_tz(e.day_date, e.start_time, trip_tz)
        if e.is_skipped:
            status = "skipped"
            skipped += 1
        elif end_utc is not None and end_utc <= now:
            status = "completed"
            completed += 1
        elif start_utc is not None and start_utc <= now:
            status = "ongoing"
        else:
            status = "upcoming"
            upcoming += 1

        summary_events.append(TodaySummaryEvent(
            event=_event_dict_for_response(e),
            status=status,
        ))

    return TodaySummaryResponse(
        date=today.isoformat(),
        total_events=len(events),
        completed=completed,
        upcoming=upcoming,
        skipped=skipped,
        events=summary_events,
    )


# ── 7. GET /{trip_id}/messages — shared trip-wide thread (3.1) ───────────────

@router.get("/{trip_id}/messages", response_model=ConciergeThreadResponse)
async def get_concierge_thread(
    trip_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The shared, trip-wide concierge thread. Readable by ALL trip members
    (including non-Plus/non-admin — an upsell surface); ``can_write`` tells the
    client whether to show the composer or a read-only/upsell state."""
    await require_trip_member(db, trip_id, current_user.id)

    stmt = (
        select(ConciergeMessage)
        .where(ConciergeMessage.trip_id == trip_id)
        .order_by(ConciergeMessage.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    names = await _author_names(db, {m.user_id for m in rows if m.user_id})

    messages = [
        ConciergeMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            message_type=m.message_type or "text",
            author_id=m.user_id,
            author_name=names.get(m.user_id),
            created_at=m.created_at.isoformat() if m.created_at else None,
            metadata=m.metadata_,
        )
        for m in rows
    ]
    can_write = await _can_write_concierge(db, trip_id, current_user)
    return ConciergeThreadResponse(messages=messages, can_write=can_write)


# ── 8. POST /{trip_id}/undo — revert the last action (3.8) ───────────────────

@router.post("/{trip_id}/undo", response_model=UndoResponse)
async def concierge_undo(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revert the most recent not-yet-undone Concierge action. Same edit gate as
    /execute (admin + Plus in v1); any eligible member can undo. Second undo of
    the same action is a no-op."""
    await require_trip_editor(db, trip_id, current_user.id)
    trip = (await db.execute(select(TripModel).where(TripModel.id == trip_id))).scalars().first()
    await entitlements.enforce_concierge(db, current_user, trip=trip)

    result = await concierge_executor.undo(db=db, trip_id=trip_id, user_id=current_user.id)

    if result.get("success"):
        await _persist_message(
            db, trip_id, current_user.id, "system",
            f"↩️ {result.get('message', 'Reverted the last action.')}",
            message_type="text",
        )

    return UndoResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        updated_events=result.get("updated_events"),
        undone_action_id=result.get("undone_action_id"),
    )
