from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.db.session import get_db
from app.models.all_models import Trip, TripMember, Event, User
from app.schemas.dashboard import TodayWidgetOut, TodayTrip, TodayEvent
from app.api.deps import get_current_user

router = APIRouter()


def _to_date(dt) -> date | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def _pick_trip(trips: list[Trip], today: date) -> tuple[str, Trip | None]:
    """Pick the most relevant trip for the Today Widget.

    Priority: in_trip (active today) > pre_trip soonest > post_trip most recent (within 30d).
    """
    in_trip: list[Trip] = []
    upcoming: list[Trip] = []
    recent_past: list[Trip] = []
    for t in trips:
        sd = _to_date(t.start_date)
        ed = _to_date(t.end_date) or sd
        if sd is None:
            continue
        if sd <= today and (ed is None or today <= ed):
            in_trip.append(t)
        elif sd > today:
            upcoming.append(t)
        elif ed is not None and 0 < (today - ed).days <= 30:
            recent_past.append(t)

    if in_trip:
        in_trip.sort(key=lambda t: _to_date(t.start_date) or today)
        return "in_trip", in_trip[0]
    if upcoming:
        upcoming.sort(key=lambda t: _to_date(t.start_date) or today)
        return "pre_trip", upcoming[0]
    if recent_past:
        recent_past.sort(key=lambda t: _to_date(t.end_date) or today, reverse=True)
        return "post_trip", recent_past[0]
    return "none", None


@router.get("/today", response_model=TodayWidgetOut)
async def get_today_widget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a contextual snapshot for the dashboard hero based on trip state."""
    today = date.today()

    stmt = (
        select(Trip)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(TripMember.user_id == current_user.id, TripMember.status == "accepted")
    )
    trips = list((await db.execute(stmt)).scalars().all())

    state, trip = _pick_trip(trips, today)
    if trip is None:
        return TodayWidgetOut(state="none")

    trip_dto = TodayTrip.model_validate(trip)
    sd = _to_date(trip.start_date)
    ed = _to_date(trip.end_date) or sd

    if state == "pre_trip" and sd is not None:
        return TodayWidgetOut(
            state=state,
            trip=trip_dto,
            days_until_start=(sd - today).days,
        )

    if state == "in_trip" and sd is not None:
        ev_stmt = (
            select(Event)
            .where(Event.trip_id == trip.id, Event.day_date == today)
            .order_by(Event.start_time.nulls_last(), Event.sort_order)
        )
        events = list((await db.execute(ev_stmt)).scalars().all())

        now = datetime.now()
        next_idx: int | None = None
        for i, e in enumerate(events):
            if e.start_time is not None and e.start_time >= now:
                next_idx = i
                break

        today_events = []
        for i, e in enumerate(events):
            today_events.append(TodayEvent(
                id=e.id,
                title=e.title,
                location_name=e.location_name,
                start_time=e.start_time,
                end_time=e.end_time,
                is_next=(i == next_idx),
            ))

        day_number = (today - sd).days + 1
        total_days = ((ed - sd).days + 1) if ed is not None else None
        return TodayWidgetOut(
            state=state,
            trip=trip_dto,
            today_date=today,
            today_events=today_events,
            day_number=day_number,
            total_days=total_days,
        )

    if state == "post_trip" and ed is not None:
        count_stmt = select(sa_func.count(Event.id)).where(Event.trip_id == trip.id)
        total_events = (await db.execute(count_stmt)).scalar_one()
        total_days = ((ed - sd).days + 1) if sd is not None else None
        return TodayWidgetOut(
            state=state,
            trip=trip_dto,
            days_since_end=(today - ed).days,
            total_events=total_events,
            total_days=total_days,
        )

    return TodayWidgetOut(state="none")
