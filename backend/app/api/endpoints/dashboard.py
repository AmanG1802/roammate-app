from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.db.session import get_db
from app.models.all_models import Trip, TripMember, TimelineItem, TripDay, User
from app.schemas.dashboard import TodayWidgetOut, TodayWidgetPage, TodayTrip, TodayEvent
from app.api.deps import get_current_user
from app.utils.tz import utc_now, from_utc, today_in_tz, combine_in_tz

router = APIRouter()


def _to_date(dt) -> date | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.date()
    return dt


MAX_PAST = 2
MAX_UPCOMING = 3

def _classify(trips: list[Trip], today: date) -> tuple[list[Trip], list[Trip], list[Trip]]:
    """Bucket and cap trips: up to 1 active, MAX_PAST past, MAX_UPCOMING upcoming.

    Past: most-recent-first (capped to last 2).
    Upcoming: soonest-first (capped to next 3).
    Active: soonest start first (only 1 ongoing trip shown).
    """
    active: list[Trip] = []
    upcoming: list[Trip] = []
    past: list[Trip] = []
    for t in trips:
        sd = _to_date(t.start_date)
        ed = _to_date(t.end_date) or sd
        if sd is None:
            continue
        if sd <= today and (ed is None or today <= ed):
            active.append(t)
        elif sd > today:
            upcoming.append(t)
        elif ed is not None and (today - ed).days > 0:
            past.append(t)
    active.sort(key=lambda t: _to_date(t.start_date) or today)
    active = active[:1]
    upcoming.sort(key=lambda t: _to_date(t.start_date) or today)
    upcoming = upcoming[:MAX_UPCOMING]
    past.sort(key=lambda t: _to_date(t.end_date) or today, reverse=True)
    past = past[:MAX_PAST]
    return active, upcoming, past


def _pick_default(n_past: int, n_active: int, past: list[Trip], upcoming: list[Trip], today: date) -> int:
    """Return the default page index. Page order: past … | active | upcoming …

    Priority: ongoing trip > temporally closer of last-past vs next-upcoming.
    """
    if n_active:
        return n_past
    if past and upcoming:
        last_end = _to_date(past[0].end_date) or today
        next_start = _to_date(upcoming[0].start_date) or today
        if (today - last_end).days <= (next_start - today).days:
            return n_past - 1
        return n_past
    if past:
        return n_past - 1
    return 0


def _trip_today(trip: Trip) -> date:
    """Determine 'today' relative to the trip's destination timezone."""
    tz_name = trip.timezone or "UTC"
    return today_in_tz(tz_name)


@router.get("/today", response_model=TodayWidgetOut)
async def get_today_widget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all trip widget pages for the dashboard carousel."""
    now = utc_now()

    stmt = (
        select(Trip)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(TripMember.user_id == current_user.id, TripMember.status == "accepted")
    )
    trips = list((await db.execute(stmt)).scalars().all())

    user_tz = current_user.timezone or "UTC"
    today = today_in_tz(user_tz)

    active, upcoming, past = _classify(trips, today)
    if not active and not upcoming and not past:
        return TodayWidgetOut()

    pages: list[TodayWidgetPage] = []

    for t in reversed(past):
        sd = _to_date(t.start_date)
        ed = _to_date(t.end_date) or sd
        count_stmt = select(sa_func.count(TimelineItem.id)).where(TimelineItem.trip_id == t.id)
        total_events = (await db.execute(count_stmt)).scalar_one()
        total_days = ((ed - sd).days + 1) if sd and ed else None
        pages.append(TodayWidgetPage(
            state="post_trip", trip=TodayTrip.model_validate(t),
            days_since_end=(today - ed).days if ed else None,
            total_events=total_events, total_days=total_days,
        ))

    for t in active:
        trip_tz = t.timezone or "UTC"
        trip_today = today_in_tz(trip_tz)
        sd = _to_date(t.start_date)
        ev_stmt = (
            select(TimelineItem)
            .where(TimelineItem.trip_id == t.id, TimelineItem.day_date == trip_today)
            .order_by(TimelineItem.start_time.nulls_last(), TimelineItem.sort_order)
        )
        events = list((await db.execute(ev_stmt)).scalars().all())

        ongoing_idx: int | None = None
        next_idx: int | None = None
        past_flags: list[bool] = [False] * len(events)
        for i, e in enumerate(events):
            # TIME-only columns now; combine with day_date in the trip's tz
            # to recover an absolute instant for "is it happening right now?"
            st = combine_in_tz(e.day_date, e.start_time, trip_tz)
            et = combine_in_tz(e.day_date, e.end_time, trip_tz)
            if st is not None and et is not None:
                if st <= now < et:
                    ongoing_idx = i
            if next_idx is None and st is not None and st > now:
                next_idx = i
            # An event is "past" once its end has elapsed. If no end_time is
            # known, treat it as past once its start has elapsed (so a 14:00
            # open-ended event still falls off the widget by 21:00).
            if et is not None and et <= now:
                past_flags[i] = True
            elif et is None and st is not None and st <= now:
                past_flags[i] = True

        today_events = [
            TodayEvent(
                id=e.id, title=e.title, location_name=e.location_name,
                start_time=e.start_time, end_time=e.end_time,
                is_next=(i == next_idx),
                is_ongoing=(i == ongoing_idx),
                is_past=past_flags[i] and i != ongoing_idx,
            )
            for i, e in enumerate(events)
        ]

        trip_days = list((await db.execute(
            select(TripDay).where(TripDay.trip_id == t.id).order_by(TripDay.date)
        )).scalars().all())
        ed = _to_date(t.end_date)
        total_days = ((ed - sd).days + 1) if sd and ed else (len(trip_days) or None)
        day_number = None
        for idx, td in enumerate(trip_days):
            if _to_date(td.date) == trip_today:
                day_number = idx + 1
                break
        if day_number is None and sd:
            day_number = (trip_today - sd).days + 1

        pages.append(TodayWidgetPage(
            state="in_trip", trip=TodayTrip.model_validate(t),
            today_date=trip_today, today_events=today_events,
            day_number=day_number, total_days=total_days,
        ))

    for t in upcoming:
        sd = _to_date(t.start_date)
        pages.append(TodayWidgetPage(
            state="pre_trip", trip=TodayTrip.model_validate(t),
            days_until_start=(sd - today).days if sd else None,
        ))

    default_idx = _pick_default(len(past), len(active), past, upcoming, today)

    return TodayWidgetOut(pages=pages, default_index=default_idx)
