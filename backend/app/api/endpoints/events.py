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
from app.schemas.trip import IngestRequest, IdeaBinItem
from app.services.ripple_engine import ripple_engine
from app.services.quick_add import quick_add_service
from app.services import notification_service
from app.services.roles import require_trip_admin
from app.schemas.notification import NotificationType
from app.api.deps import get_current_user


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
    return Event(
        id=event.id, trip_id=event.trip_id, title=event.title,
        place_id=event.place_id, location_name=event.location_name,
        lat=event.lat, lng=event.lng, day_date=event.day_date,
        start_time=event.start_time, end_time=event.end_time,
        is_locked=event.is_locked, event_type=event.event_type,
        sort_order=event.sort_order, added_by=event.added_by,
        up=up, down=down, my_vote=mine,
    )

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
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Transfer votes from the source idea (if this came from the idea bin)
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
        added_by=event.added_by,
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
        url_source=idea.url_source, time_hint=idea.time_hint, added_by=idea.added_by,
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


@router.post("/quick-add/{trip_id}", response_model=Event)
async def quick_add_event(
    trip_id: int,
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    NLP Quick Add: Parses text like "Colosseum tour at 2pm" and creates a scheduled event.
    """
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    try:
        event = await quick_add_service.process_text(
            db=db,
            trip_id=trip_id,
            text=request.text,
        )
        recipients = await notification_service.trip_member_ids(
            db, trip_id, exclude_user_id=current_user.id
        )
        if recipients:
            await notification_service.emit(
                db,
                recipient_ids=recipients,
                type=NotificationType.EVENT_ADDED,
                payload={"event_id": event.id, "title": event.title, "via": "quick_add"},
                actor_id=current_user.id,
                trip_id=trip_id,
            )
            await db.commit()
        return await _event_with_votes(db, event, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
