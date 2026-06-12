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
from datetime import timedelta

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
    ExecuteRequest,
    ExecuteResponse,
    FindNearbyRequest,
    FindNearbyResponse,
    PlaceCard,
    SkipEventRequest,
    TodaySummaryEvent,
    TodaySummaryResponse,
    WhatsNextResponse,
)
from app.services.concierge_executor import concierge_executor
from app.services.google_maps import RoutePoint, get_google_maps_service
from app.services.llm.registry import get_concierge_client
from app.services.roles import require_trip_member
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


def _build_travel_times(events: list[EventModel]) -> str:
    active = [e for e in events if not e.is_skipped and e.start_time]
    if len(active) < 2:
        return "Not enough events for travel time data."
    lines = []
    for i in range(len(active) - 1):
        lines.append(f"{active[i].title} -> {active[i+1].title}: (will be computed on demand)")
    return "\n".join(lines)


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


async def _load_history(
    db: AsyncSession, trip_id: int, user_id: int, limit: int = 10,
) -> list[dict[str, str]]:
    stmt = (
        select(ConciergeMessage)
        .where(
            ConciergeMessage.trip_id == trip_id,
            ConciergeMessage.user_id == user_id,
            ConciergeMessage.role.in_(["user", "assistant"]),
        )
        .order_by(ConciergeMessage.created_at.desc())
        .limit(limit)
    )
    messages = list((await db.execute(stmt)).scalars().all())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


# ── 1. POST /{trip_id}/chat — LLM dispatch ──────────────────────────────────

@router.post("/{trip_id}/chat", response_model=ConciergeChatResponse)
async def concierge_chat(
    trip_id: int,
    body: ConciergeChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)
    trip = (await db.execute(select(TripModel).where(TripModel.id == trip_id))).scalars().first()
    if trip is not None and trip.is_tutorial_completed:
        raise HTTPException(status_code=423, detail={"code": "tutorial_locked"})
    await entitlements.enforce_concierge(db, current_user, trip=trip)

    if trip is not None and trip.is_tutorial:
        from app.services.tutorial_fixtures import CANNED_CONCIERGE_REPLIES
        prior = await _load_history(db, trip_id, current_user.id)
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

    events = await _load_today_events(db, trip_id, trip_tz)
    events_list = _build_events_list(events, trip_tz)
    travel_times = _build_travel_times(events)
    current_time = local_now.strftime("%Y-%m-%d %H:%M")

    history = await _load_history(db, trip_id, current_user.id)

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

    return ConciergeChatResponse(
        intent=result["intent"],
        user_message=result["user_message"],
        params=result.get("params", {}),
        requires_confirmation=result.get("requires_confirmation", True),
        message_type=message_type,
    )


# ── 2. POST /{trip_id}/execute — confirm & execute ──────────────────────────

@router.post("/{trip_id}/execute", response_model=ExecuteResponse)
async def concierge_execute(
    trip_id: int,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)
    await entitlements.enforce_concierge(db, current_user)

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
    await require_trip_member(db, trip_id, current_user.id)
    await entitlements.enforce_concierge(db, current_user)

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
