from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from typing import List
from app.db.session import get_db
from app.models.all_models import (
    Event as EventModel, TripMember, User,
    IdeaBinItem as IdeaBinItemModel, IdeaVote, EventVote,
)
from app.schemas.event import Event, EventCreate, EventUpdate, RippleRequest
from app.schemas.trip import IdeaBinItem
from app.services.ripple_engine import ripple_engine
from app.services import notification_service
from app.services.roles import require_trip_admin
from app.schemas.notification import NotificationType
from app.api.deps import get_current_user


_ENRICH_FIELDS = (
    "description", "category", "address", "photo_url", "rating",
    "price_level", "types", "opening_hours", "phone", "website", "time_category",
)


def _event_to_schema(event: EventModel, up: int, down: int, mine: int) -> Event:
    return Event(
        id=event.id, trip_id=event.trip_id, title=event.title,
        place_id=event.place_id, location_name=event.location_name,
        lat=event.lat, lng=event.lng, day_date=event.day_date,
        start_time=event.start_time, end_time=event.end_time,
        is_locked=event.is_locked, event_type=event.event_type,
        sort_order=event.sort_order, added_by=event.added_by,
        description=event.description, category=event.category,
        address=event.address, photo_url=event.photo_url, rating=event.rating,
        price_level=event.price_level, types=event.types,
        opening_hours=event.opening_hours, phone=event.phone, website=event.website,
        time_category=event.time_category,
        up=up, down=down, my_vote=mine,
    )


async def _event_with_votes(db, event: EventModel, user_id: int) -> Event:
    """Build an Event response schema with vote tallies attached."""
    up = (await db.execute(
        select(sa_func.count(EventVote.id)).where(EventVote.event_id == event.id, EventVote.value == 1)
    )).scalar_one()
    down = (await db.execute(
        select(sa_func.count(EventVote.id)).where(EventVote.event_id == event.id, EventVote.value == -1)
    )).scalar_one()
    mine = (await db.execute(
        select(EventVote.value).where(EventVote.event_id == event.id, EventVote.user_id == user_id)
    )).scalars().first() or 0
    return _event_to_schema(event, up, down, mine)

router = APIRouter()


@router.post("/", response_model=Event, status_code=201)
async def create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single event (e.g. from idea bin drag-to-timeline)."""
    stmt = select(TripMember).where(
        TripMember.trip_id == event_in.trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    event = EventModel(
        trip_id=event_in.trip_id,
        title=event_in.title,
        place_id=event_in.place_id,
        location_name=event_in.location_name,
        lat=event_in.lat,
        lng=event_in.lng,
        day_date=event_in.day_date,
        start_time=event_in.start_time,
        end_time=event_in.end_time,
        is_locked=event_in.is_locked,
        event_type=event_in.event_type,
        sort_order=event_in.sort_order,
        added_by=event_in.added_by,
        description=event_in.description,
        category=event_in.category,
        address=event_in.address,
        photo_url=event_in.photo_url,
        rating=event_in.rating,
        price_level=event_in.price_level,
        types=event_in.types,
        opening_hours=event_in.opening_hours,
        phone=event_in.phone,
        website=event_in.website,
        time_category=event_in.time_category,
    )

    # Carry Google Maps enrichment + votes from the source idea (if any)
    if event_in.source_idea_id is not None:
        src_idea = (await db.execute(
            select(IdeaBinItemModel).where(IdeaBinItemModel.id == event_in.source_idea_id)
        )).scalars().first()
        if src_idea is not None:
            for f in _ENRICH_FIELDS:
                if getattr(event, f) is None:
                    setattr(event, f, getattr(src_idea, f, None))
            if not event.place_id:
                event.place_id = src_idea.place_id
            if not event.location_name:
                event.location_name = src_idea.address or event.location_name

    db.add(event)
    await db.commit()
    await db.refresh(event)

    if event_in.source_idea_id is not None:
        src_votes = (await db.execute(
            select(IdeaVote).where(IdeaVote.idea_id == event_in.source_idea_id)
        )).scalars().all()
        for v in src_votes:
            db.add(EventVote(event_id=event.id, user_id=v.user_id, value=v.value))
        if src_votes:
            await db.commit()

    recipients = await notification_service.trip_member_ids(
        db, event.trip_id, exclude_user_id=current_user.id
    )
    if recipients:
        await notification_service.emit(
            db,
            recipient_ids=recipients,
            type=NotificationType.EVENT_ADDED,
            payload={"event_id": event.id, "title": event.title},
            actor_id=current_user.id,
            trip_id=event.trip_id,
        )
        await db.commit()
    return await _event_with_votes(db, event, current_user.id)


@router.patch("/{event_id}", response_model=Event)
async def update_event(
    event_id: int,
    update: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update event time or sort_order."""
    stmt = select(EventModel).where(EventModel.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Verify membership
    stmt = select(TripMember).where(
        TripMember.trip_id == event.trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    time_changed = False
    if update.title is not None:
        event.title = update.title
    if update.day_date is not None and update.day_date != event.day_date:
        event.day_date = update.day_date
        time_changed = True
    if update.start_time is not None and update.start_time != event.start_time:
        event.start_time = update.start_time
        time_changed = True
    if update.end_time is not None:
        event.end_time = update.end_time
    if update.sort_order is not None:
        event.sort_order = update.sort_order
    if update.time_category is not None:
        event.time_category = update.time_category

    await db.commit()
    await db.refresh(event)

    if time_changed:
        recipients = await notification_service.trip_member_ids(
            db, event.trip_id, exclude_user_id=current_user.id
        )
        if recipients:
            await notification_service.emit(
                db,
                recipient_ids=recipients,
                type=NotificationType.EVENT_MOVED,
                payload={"event_id": event.id, "title": event.title},
                actor_id=current_user.id,
                trip_id=event.trip_id,
            )
            await db.commit()
    return await _event_with_votes(db, event, current_user.id)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an event (e.g. when sending back to idea bin)."""
    stmt = select(EventModel).where(EventModel.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(TripMember).where(
        TripMember.trip_id == event.trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    trip_id = event.trip_id
    title = event.title
    await db.delete(event)
    await db.commit()

    recipients = await notification_service.trip_member_ids(
        db, trip_id, exclude_user_id=current_user.id
    )
    if recipients:
        await notification_service.emit(
            db,
            recipient_ids=recipients,
            type=NotificationType.EVENT_REMOVED,
            payload={"title": title},
            actor_id=current_user.id,
            trip_id=trip_id,
        )
        await db.commit()


@router.post("/{event_id}/move-to-bin", response_model=IdeaBinItem)
async def move_event_to_bin(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atomically move an event back to the idea bin, preserving added_by."""
    stmt = select(EventModel).where(EventModel.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(TripMember).where(
        TripMember.trip_id == event.trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    hint = None
    if event.start_time:
        h = event.start_time.hour
        m = event.start_time.minute
        ampm = "pm" if h >= 12 else "am"
        h12 = h % 12 or 12
        hint = f"{h12}:{m:02d}{ampm}" if m else f"{h12}{ampm}"

    idea = IdeaBinItemModel(
        trip_id=event.trip_id,
        title=event.title,
        place_id=event.place_id,
        lat=event.lat,
        lng=event.lng,
        time_hint=hint,
        time_category=event.time_category,
        added_by=event.added_by,
        description=event.description,
        category=event.category,
        address=event.address,
        photo_url=event.photo_url,
        rating=event.rating,
        price_level=event.price_level,
        types=event.types,
        opening_hours=event.opening_hours,
        phone=event.phone,
        website=event.website,
    )
    trip_id = event.trip_id
    title = event.title
    db.add(idea)
    await db.flush()

    # Transfer votes: EventVote rows -> IdeaVote rows on the new idea
    src_votes = (await db.execute(
        select(EventVote).where(EventVote.event_id == event.id)
    )).scalars().all()
    for v in src_votes:
        db.add(IdeaVote(idea_id=idea.id, user_id=v.user_id, value=v.value))

    await db.delete(event)
    await db.commit()
    await db.refresh(idea)

    recipients = await notification_service.trip_member_ids(
        db, trip_id, exclude_user_id=current_user.id
    )
    if recipients:
        await notification_service.emit(
            db,
            recipient_ids=recipients,
            type=NotificationType.EVENT_REMOVED,
            payload={"title": title, "moved_to_bin": True},
            actor_id=current_user.id,
            trip_id=trip_id,
        )
        await db.commit()

    up = (await db.execute(
        select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea.id, IdeaVote.value == 1)
    )).scalar_one()
    down = (await db.execute(
        select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea.id, IdeaVote.value == -1)
    )).scalar_one()
    mine = (await db.execute(
        select(IdeaVote.value).where(IdeaVote.idea_id == idea.id, IdeaVote.user_id == current_user.id)
    )).scalars().first() or 0
    return IdeaBinItem(
        id=idea.id, trip_id=idea.trip_id, title=idea.title,
        place_id=idea.place_id, lat=idea.lat, lng=idea.lng,
        url_source=idea.url_source, time_hint=idea.time_hint, time_category=idea.time_category,
        added_by=idea.added_by, description=idea.description, category=idea.category,
        address=idea.address, photo_url=idea.photo_url, rating=idea.rating,
        price_level=idea.price_level, types=idea.types, opening_hours=idea.opening_hours,
        phone=idea.phone, website=idea.website,
        up=up, down=down, my_vote=mine,
    )


@router.get("/", response_model=List[Event])
async def get_events(
    trip_id: int = Query(..., description="Trip to fetch events for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all events for a trip the current user is a member of."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(EventModel).where(EventModel.trip_id == trip_id)
    events = (await db.execute(stmt)).scalars().all()

    event_ids = [e.id for e in events]
    if not event_ids:
        return []

    up_stmt = (
        select(EventVote.event_id, sa_func.count(EventVote.id))
        .where(EventVote.event_id.in_(event_ids), EventVote.value == 1)
        .group_by(EventVote.event_id)
    )
    up_map = dict((await db.execute(up_stmt)).all())

    down_stmt = (
        select(EventVote.event_id, sa_func.count(EventVote.id))
        .where(EventVote.event_id.in_(event_ids), EventVote.value == -1)
        .group_by(EventVote.event_id)
    )
    down_map = dict((await db.execute(down_stmt)).all())

    my_stmt = (
        select(EventVote.event_id, EventVote.value)
        .where(EventVote.event_id.in_(event_ids), EventVote.user_id == current_user.id)
    )
    my_map = dict((await db.execute(my_stmt)).all())

    return [
        Event(
            id=e.id, trip_id=e.trip_id, title=e.title,
            place_id=e.place_id, location_name=e.location_name,
            lat=e.lat, lng=e.lng, day_date=e.day_date,
            start_time=e.start_time, end_time=e.end_time,
            is_locked=e.is_locked, event_type=e.event_type,
            sort_order=e.sort_order, added_by=e.added_by,
            description=e.description, category=e.category,
            address=e.address, photo_url=e.photo_url, rating=e.rating,
            price_level=e.price_level, types=e.types,
            opening_hours=e.opening_hours, phone=e.phone, website=e.website,
            time_category=e.time_category,
            up=up_map.get(e.id, 0), down=down_map.get(e.id, 0),
            my_vote=my_map.get(e.id, 0),
        )
        for e in events
    ]


@router.post("/ripple/{trip_id}", response_model=List[Event])
async def trigger_ripple_engine(
    trip_id: int,
    request: RippleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger the Ripple Engine to shift all subsequent events.
    Used for "Running Late" or manual time adjustments.
    Only trip admins can fire ripples.
    """
    await require_trip_admin(db, trip_id, current_user.id)

    try:
        updated_events = await ripple_engine.shift_itinerary(
            db=db,
            trip_id=trip_id,
            delta_minutes=request.delta_minutes,
            start_from_time=request.start_from_time,
        )
        if updated_events:
            recipients = await notification_service.trip_member_ids(
                db, trip_id, exclude_user_id=current_user.id
            )
            if recipients:
                await notification_service.emit(
                    db,
                    recipient_ids=recipients,
                    type=NotificationType.RIPPLE_FIRED,
                    payload={
                        "delta_minutes": request.delta_minutes,
                        "shifted_count": len(updated_events),
                    },
                    actor_id=current_user.id,
                    trip_id=trip_id,
                )
                await db.commit()
        return [await _event_with_votes(db, e, current_user.id) for e in updated_events]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
